// SAFE: Android EncryptedSharedPreferences (AndroidX Security) per token storage.
package it.siae.synthetic

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

class AuthRepositorySafe(context: Context) {
    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()

    private val prefs = EncryptedSharedPreferences.create(
        context, "auth_secure", masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )

    // SAFE: token encrypted-at-rest via AndroidX Security
    fun saveToken(jwt: String) {
        prefs.edit().putString("token", jwt).apply()
    }
}
