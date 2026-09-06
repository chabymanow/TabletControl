package com.chaby.tabletcontrol.network

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.net.HttpURLConnection
import java.net.URL

data class ConnectionResult(
    val success: Boolean,
    val message: String = ""
)

object ConnectionChecker
{
    suspend fun check(ip: String, port: String): ConnectionResult
    {
        return withContext(Dispatchers.IO)
        {
            val url = "http://$ip:$port/api/stats"

            try
            {
                val connection = URL(url).openConnection() as HttpURLConnection

                connection.requestMethod = "GET"
                connection.connectTimeout = 3000
                connection.readTimeout = 3000
                connection.useCaches = false

                val responseCode = connection.responseCode

                connection.disconnect()

                if (responseCode == HttpURLConnection.HTTP_OK)
                {
                    ConnectionResult(
                        success = true,
                        message = "Connected"
                    )
                }
                else
                {
                    ConnectionResult(
                        success = false,
                        message = "TabletControl returned HTTP $responseCode."
                    )
                }
            }
            catch (exception: Exception)
            {
                ConnectionResult(
                    success = false,
                    message = "Could not connect to $ip:$port."
                )
            }
        }
    }
}