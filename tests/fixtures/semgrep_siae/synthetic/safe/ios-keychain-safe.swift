// SAFE: iOS Keychain Services per token storage (encrypted, hardware-backed).
import Foundation
import Security

class AuthRepositorySafe {
    // SAFE: keychain encrypted-at-rest, hardware-backed Secure Enclave su device A12+
    func saveTokenToKeychain(_ jwt: String) {
        let data = jwt.data(using: .utf8)!
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: "auth_token",
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
        ]
        SecItemDelete(query as CFDictionary)
        SecItemAdd(query as CFDictionary, nil)
    }

    // SAFE: non-secret data in UserDefaults (UI preferences) → no PII
    func saveLastViewedReport(_ id: String) {
        UserDefaults.standard.set(id, forKey: "last_viewed_report_id")
    }
}
