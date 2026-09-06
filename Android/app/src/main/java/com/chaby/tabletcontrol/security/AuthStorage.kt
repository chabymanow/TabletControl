package com.chaby.tabletcontrol.security

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

object AuthStorage
{
    private const val KEY_ALIAS = "tabletcontrol_auth_key"
    private const val PREFERENCES_NAME = "tabletcontrol_secure_settings"
    private const val TOKEN_KEY = "auth_token"
    private const val IV_KEY = "auth_token_iv"

    private fun getSecretKey(): SecretKey
    {
        val keyStore = KeyStore.getInstance("AndroidKeyStore")
        keyStore.load(null)

        val existingKey = keyStore.getKey(KEY_ALIAS, null)

        if (existingKey is SecretKey)
        {
            return existingKey
        }

        val keyGenerator = KeyGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_AES,
            "AndroidKeyStore"
        )

        val specification = KeyGenParameterSpec.Builder(
            KEY_ALIAS,
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
        )
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .build()

        keyGenerator.init(specification)

        return keyGenerator.generateKey()
    }

    fun saveToken(context: Context, token: String)
    {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, getSecretKey())

        val encryptedToken = cipher.doFinal(token.toByteArray(Charsets.UTF_8))

        val preferences = context.getSharedPreferences(
            PREFERENCES_NAME,
            Context.MODE_PRIVATE
        )

        preferences.edit()
            .putString(
                TOKEN_KEY,
                Base64.encodeToString(encryptedToken, Base64.NO_WRAP)
            )
            .putString(
                IV_KEY,
                Base64.encodeToString(cipher.iv, Base64.NO_WRAP)
            )
            .apply()
    }

    fun getToken(context: Context): String
    {
        val preferences = context.getSharedPreferences(
            PREFERENCES_NAME,
            Context.MODE_PRIVATE
        )

        val encryptedValue = preferences.getString(TOKEN_KEY, null) ?: return ""
        val ivValue = preferences.getString(IV_KEY, null) ?: return ""

        return try
        {
            val encryptedToken = Base64.decode(encryptedValue, Base64.NO_WRAP)
            val iv = Base64.decode(ivValue, Base64.NO_WRAP)

            val cipher = Cipher.getInstance("AES/GCM/NoPadding")

            cipher.init(
                Cipher.DECRYPT_MODE,
                getSecretKey(),
                GCMParameterSpec(128, iv)
            )

            String(
                cipher.doFinal(encryptedToken),
                Charsets.UTF_8
            )
        }
        catch (exception: Exception)
        {
            ""
        }
    }

    fun clearToken(context: Context)
    {
        val preferences = context.getSharedPreferences(
            PREFERENCES_NAME,
            Context.MODE_PRIVATE
        )

        preferences.edit()
            .remove(TOKEN_KEY)
            .remove(IV_KEY)
            .apply()
    }
}