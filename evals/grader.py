#!/usr/bin/env python3
"""
grader.py — LLM-as-judge per eval funzionali e e2e.

Chiama Opus 4.5 via AWS Bedrock direttamente con boto3.
Nessun uso di `claude -p` — zero conflitti con Claude Code subscription.
Nessun fallback — se Bedrock non e' raggiungibile, fallisce esplicitamente.
"""

import json
import os

import boto3
from botocore.config import Config as BotoConfig

GRADER_MODEL = "eu.anthropic.claude-opus-4-5-20251101-v1:0"

GRADER_PROMPT_TEMPLATE = """Sei un valutatore rigoroso di skill AI. Analizza l'output di un agente
e assegna un punteggio 0-5 per ogni criterio.

## Output dell'agente

{agent_output}

## Criteri di valutazione

{criteria_json}

Per OGNI criterio rispondi con:
- name: il nome del criterio (esattamente come fornito)
- score: 0-5 (0=completamente assente, 3=parziale, 5=perfetto)
- reasoning: una frase di motivazione

Rispondi SOLO con un JSON valido, nessun altro testo:
{{"scores": [{{"name": "...", "score": N, "reasoning": "..."}}]}}"""


def _get_bedrock_client():
    """Crea client Bedrock Runtime con config appropriata."""
    region = os.environ.get("AWS_REGION", "eu-west-1")
    config = BotoConfig(
        region_name=region,
        read_timeout=120,
        retries={"max_attempts": 2, "mode": "adaptive"},
    )
    return boto3.client("bedrock-runtime", config=config)


def _call_bedrock(prompt: str, timeout: int = 120) -> str:
    """Chiama Bedrock Invoke Model API con Opus 4.5.

    Returns:
        Testo della risposta del modello.

    Raises:
        RuntimeError: se la chiamata fallisce.
    """
    client = _get_bedrock_client()

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0,
    })

    try:
        response = client.invoke_model(
            modelId=GRADER_MODEL,
            contentType="application/json",
            accept="application/json",
            body=body,
        )
        result = json.loads(response["body"].read())
        # Estrai testo dalla risposta Bedrock
        content = result.get("content", [])
        text_parts = [c["text"] for c in content if c.get("type") == "text"]
        return "\n".join(text_parts).strip()

    except client.exceptions.AccessDeniedException as e:
        raise RuntimeError(
            f"Bedrock AccessDenied — verifica credenziali AWS e permessi per {GRADER_MODEL}: {e}"
        )
    except Exception as e:
        raise RuntimeError(f"Bedrock invoke_model fallito: {e}")


def grade(agent_output: str, criteria: list[dict], timeout: int = 120) -> dict:
    """Chiama Opus 4.5 Bedrock come LLM-as-judge.

    Args:
        agent_output: output completo dell'agente da valutare
        criteria: lista di {"name", "weight", "check"}
        timeout: secondi max per la chiamata

    Returns:
        {"scores": [{"name", "score", "reasoning"}], "weighted_score": float, "pass": None}
        (pass viene calcolato dal chiamante con la sua threshold)

    Raises:
        RuntimeError: se Bedrock non raggiungibile o grader fallisce dopo retry
    """
    criteria_json = json.dumps(criteria, indent=2, ensure_ascii=False)
    prompt = GRADER_PROMPT_TEMPLATE.format(
        agent_output=agent_output[:15000],
        criteria_json=criteria_json,
    )

    for attempt in range(2):
        try:
            raw = _call_bedrock(prompt, timeout=timeout)

            # Estrai JSON dalla risposta
            json_str = raw
            if "```json" in raw:
                json_str = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                json_str = raw.split("```")[1].split("```")[0].strip()

            parsed = json.loads(json_str)
            scores = parsed.get("scores", [])

            # Calcola weighted score
            total_weight = sum(c["weight"] for c in criteria)
            weighted_sum = 0
            for s in scores:
                matching = [c for c in criteria if c["name"] == s["name"]]
                weight = matching[0]["weight"] if matching else 1
                weighted_sum += s["score"] * weight

            weighted_score = weighted_sum / (5 * total_weight) if total_weight > 0 else 0

            return {
                "scores": scores,
                "weighted_score": round(weighted_score, 3),
                "pass": None,
            }

        except json.JSONDecodeError:
            if attempt == 0:
                prompt = prompt + "\n\nIMPORTANTE: rispondi SOLO con JSON valido. Nessun testo prima o dopo."
                continue
            raise RuntimeError(f"Grader ha prodotto JSON non valido dopo retry: {raw[:200]}")
        except RuntimeError:
            raise
        except Exception as e:
            if attempt == 0:
                continue
            raise RuntimeError(f"Grader fallito dopo retry: {e}")

    raise RuntimeError("Grader fallito: tentativi esauriti")
