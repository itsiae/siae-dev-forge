// SAFE Angular: usa template interpolation {{}}, no bypassSecurityTrust*.

import { Component } from "@angular/core";

@Component({
  selector: "app-safe",
  // Template interpolation {{}} usa Angular built-in escape (XSS-safe)
  template: "<div>{{userText}}</div>",
})
export class SafeComponent {
  userText: string = "user-input-here";  // automatically escaped by Angular
}
