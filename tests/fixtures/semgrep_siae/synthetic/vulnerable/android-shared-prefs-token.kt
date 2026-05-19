// Android Kotlin: SharedPreferences plaintext token storage (CWE-312).
package it.siae.synthetic

import android.content.Context
import android.content.SharedPreferences

class AuthRepositoryVulnerable(context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences("auth", Context.MODE_PRIVATE)

    // VULNERABLE: token JWT in cleartext on disk — leak su root/backup/forensic
    fun saveToken(jwt: String) {
        prefs.edit().putString("token", jwt).apply()
    }

    fun saveAccessToken(accessToken: String) {
        prefs.edit().putString("access_token", accessToken).apply()
    }

    fun saveJwt(t: String) {
        prefs.edit().putString("jwt", t).commit()
    }
}
