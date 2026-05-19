// F19: Vue v-html + React dangerouslySetInnerHTML su untrusted input (CWE-79).
import React from "react";

// React VULNERABLE: dangerouslySetInnerHTML
export function VulnReactComponent(props: { userInput: string }) {
  return <div dangerouslySetInnerHTML={{ __html: props.userInput }} />;
}

// React VULNERABLE: DOMPurify config permissivo (ALLOWED_TAGS wildcard)
import DOMPurify from "dompurify";
export function VulnDOMPurifyPermissive(props: { userInput: string }) {
  const sanitized = DOMPurify.sanitize(props.userInput, { ALLOWED_TAGS: ["*"] });
  return <div dangerouslySetInnerHTML={{ __html: sanitized }} />;
}
