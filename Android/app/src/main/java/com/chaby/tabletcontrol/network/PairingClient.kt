package com.chaby.tabletcontrol.network

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

data class PairingStatusResult(
    val success: Boolean,
    val authenticationRequired: Boolean = false,
    val pairingActive: Boolean = false,
    val expiresIn: Int = 0,
    val message: String = ""
)

data class PairingResult(
    val success: Boolean,
    val token: String = "",
    val deviceId: String = "",
    val message: String = ""
)

object PairingClient
{
    suspend fun getStatus(ip: String, port: String): PairingStatusResult
    {
        return withContext(Dispatchers.IO) {
            val connection = URL(
                "http://$ip:$port/api/pair/status"
            ).openConnection() as HttpURLConnection

            try
            {
                connection.requestMethod = "GET"
                connection.connectTimeout = 3000
                connection.readTimeout = 3000
                connection.useCaches = false
                connection.setRequestProperty("Accept", "application/json")

                val responseCode = connection.responseCode
                val responseBody = readResponse(connection, responseCode)

                if (responseCode !in 200..299)
                {
                    return@withContext PairingStatusResult(
                        success = false,
                        message = "TabletControl returned HTTP $responseCode."
                    )
                }

                val json = JSONObject(responseBody)

                PairingStatusResult(
                    success = json.optBoolean("success", false),
                    authenticationRequired = json.optBoolean("authentication_required", false),
                    pairingActive = json.optBoolean("pairing_active", false),
                    expiresIn = json.optInt("expires_in", 0)
                )
            }
            catch (exception: Exception)
            {
                PairingStatusResult(
                    success = false,
                    message = "Could not contact TabletControl."
                )
            }
            finally
            {
                connection.disconnect()
            }
        }
    }

    suspend fun pair(
        ip: String,
        port: String,
        code: String,
        deviceName: String = "Android Tablet"
    ): PairingResult
    {
        return withContext(Dispatchers.IO) {
            val connection = URL(
                "http://$ip:$port/api/pair"
            ).openConnection() as HttpURLConnection

            try
            {
                val requestBody = JSONObject().apply {
                    put("code", code.trim())
                    put("device_name", deviceName)
                }

                connection.requestMethod = "POST"
                connection.connectTimeout = 3000
                connection.readTimeout = 3000
                connection.useCaches = false
                connection.doOutput = true

                connection.setRequestProperty(
                    "Content-Type",
                    "application/json; charset=utf-8"
                )

                connection.setRequestProperty(
                    "Accept",
                    "application/json"
                )

                connection.outputStream.use { output ->
                    output.write(
                        requestBody.toString().toByteArray(Charsets.UTF_8)
                    )
                }

                val responseCode = connection.responseCode
                val responseBody = readResponse(connection, responseCode)

                if (responseBody.isBlank())
                {
                    return@withContext PairingResult(
                        success = false,
                        message = "TabletControl returned an empty response."
                    )
                }

                val json = JSONObject(responseBody)

                if (responseCode !in 200..299)
                {
                    return@withContext PairingResult(
                        success = false,
                        message = json.optString(
                            "message",
                            "Pairing failed."
                        )
                    )
                }

                val token = json.optString("token")
                val deviceId = json.optString("device_id")

                if (token.isBlank())
                {
                    return@withContext PairingResult(
                        success = false,
                        message = "TabletControl did not return an authentication token."
                    )
                }

                PairingResult(
                    success = true,
                    token = token,
                    deviceId = deviceId
                )
            }
            catch (exception: Exception)
            {
                PairingResult(
                    success = false,
                    message = "Could not pair with TabletControl."
                )
            }
            finally
            {
                connection.disconnect()
            }
        }
    }

    private fun readResponse(
        connection: HttpURLConnection,
        responseCode: Int
    ): String
    {
        val stream = if (responseCode in 200..299)
        {
            connection.inputStream
        }
        else
        {
            connection.errorStream
        }

        if (stream == null)
        {
            return ""
        }

        return stream.bufferedReader().use { reader ->
            reader.readText()
        }
    }
}