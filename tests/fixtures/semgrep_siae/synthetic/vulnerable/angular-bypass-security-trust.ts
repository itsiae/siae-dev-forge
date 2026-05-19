// Wave 3 cross-stack porting: Angular DomSanitizer bypassSecurityTrust* (CWE-79 XSS).
// Synthetic minimal repro, no broadcasting code.

import { Component } from "@angular/core";
import { DomSanitizer, SafeHtml } from "@angular/platform-browser";

@Component({ selector: "app-vuln", template: "<div [innerHTML]='safeHtml'></div>" })
export class VulnComponent {
  safeHtml: SafeHtml;

  constructor(private sanitizer: DomSanitizer) {
    // VULNERABLE: trust su input untrusted bypassa Angular sanitization
    const userHtml = this.getUserInput();
    this.safeHtml = this.sanitizer.bypassSecurityTrustHtml(userHtml);
  }

  exfilUrl(url: string) {
    // VULNERABLE: bypass su URL → open redirect / data: scheme
    return this.sanitizer.bypassSecurityTrustUrl(url);
  }

  resourceUrl(url: string) {
    // VULNERABLE: bypassSecurityTrustResourceUrl (iframe src injection)
    return this.sanitizer.bypassSecurityTrustResourceUrl(url);
  }

  getUserInput(): string { return "user-input-here"; }
}
