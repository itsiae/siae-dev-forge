// iOS Swift: UserDefaults plaintext token storage (CWE-312).
// Stack mobile SIAE: Swift native.
import Foundation

class AuthRepositoryVulnerable {
    private let defaults = UserDefaults.standard

    // VULNERABLE: token in UserDefaults plist plain (CWE-312)
    func saveToken(_ jwt: String) {
        defaults.set(jwt, forKey: "token")
    }

    func saveAccessToken(_ token: String) {
        defaults.set(token, forKey: "access_token")
    }

    func saveJwt(_ t: String) {
        UserDefaults.standard.set(t, forKey: "jwt")
    }
}
