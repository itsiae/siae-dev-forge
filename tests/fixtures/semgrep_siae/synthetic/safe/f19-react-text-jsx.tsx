// SAFE: React JSX text interpolation auto-escape XSS.
import React from "react";

export function SafeReactComponent(props: { userInput: string }) {
  // JSX {} auto-escape — XSS-safe by-default
  return <div>{props.userInput}</div>;
}

// SAFE: DOMPurify default config (no ALLOWED_TAGS wildcard)
import DOMPurify from "dompurify";
export function SafeDOMPurifyDefault(props: { userInput: string }) {
  const sanitized = DOMPurify.sanitize(props.userInput);
  return <div dangerouslySetInnerHTML={{ __html: sanitized }} />;
}
