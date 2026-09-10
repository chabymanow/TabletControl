package com.chaby.tabletcontrol.network

import android.os.Build
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

data class DisconnectResult(
    val success: Boolean,
    val message: String = ""
)

object PairingClient
{
    private fun getDeviceName(): String
    {
        val manufacturer = Build.MANUFACTURER.orEmpty().trim()
        val model = Build.MODEL.orEmpty().trim()
        val displayManufacturer = manufacturer.replaceFirstChar { character ->
            character.uppercase()
        }

        return when
        {
            manufacturer.isBlank() && model.isBlank() -> "Android Tablet"
            manufacturer.isBlank() -> model
            model.isBlank() -> displayManufacturer
            model.startsWith(manufacturer, ignoreCase = true) -> model
            else -> "$displayManufacturer $model"
        }.take(80)
    }

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
        deviceName: String = getDeviceName()
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

    suspend fun disconnect(
        ip: String,
        port: String,
        token: String
    ): DisconnectResult
    {
        if (token.isBlank())
        {
            return DisconnectResult(success = true)
        }

        return withContext(Dispatchers.IO) {
            val connection = URL(
                "http://$ip:$port/api/pair/unpair"
            ).openConnection() as HttpURLConnection

            try
            {
                connection.requestMethod = "POST"
                connection.connectTimeout = 3000
                connection.readTimeout = 3000
                connection.useCaches = false
                connection.doOutput = true
                connection.setFixedLengthStreamingMode(0)
                connection.setRequestProperty("Accept", "application/json")
                connection.setRequestProperty("Authorization", "Bearer $token")

                connection.outputStream.use { }

                val responseCode = connection.responseCode
                val responseBody = readResponse(connection, responseCode)

                val responseMessage = try
                {
                    JSONObject(responseBody).optString("message", "")
                }
                catch (exception: Exception)
                {
                    ""
                }

                if (responseCode == 401)
                {
                    return@withContext DisconnectResult(success = true)
                }

                if (responseCode == 404 && responseMessage == "Device not found.")
                {
                    return@withContext DisconnectResult(success = true)
                }

                if (responseCode !in 200..299)
                {
                    val message = if (responseCode == 404)
                    {
                        "This PC does not support remote disconnect yet. Update and restart the TabletControl PC agent first."
                    }
                    else
                    {
                        responseMessage.ifBlank {
                            "TabletControl returned HTTP $responseCode."
                        }
                    }

                    return@withContext DisconnectResult(
                        success = false,
                        message = message
                    )
                }

                DisconnectResult(success = true)
            }
            catch (exception: Exception)
            {
                DisconnectResult(
                    success = false,
                    message = "Could not contact the PC to remove this tablet."
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
