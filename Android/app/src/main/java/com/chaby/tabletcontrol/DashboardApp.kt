package com.chaby.tabletcontrol

import android.content.Context
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.getValue
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import com.chaby.tabletcontrol.network.PairingClient
import com.chaby.tabletcontrol.security.AuthStorage
import com.chaby.tabletcontrol.ui.DashboardScreen
import com.chaby.tabletcontrol.ui.SettingsScreen

@Composable
fun DashboardApp()
{
    val context = LocalContext.current

    val preferences = remember {
        context.getSharedPreferences(
            "dashboard_settings",
            Context.MODE_PRIVATE
        )
    }

    var serverIp by rememberSaveable {
        mutableStateOf(
            preferences.getString("server_ip", "") ?: ""
        )
    }

    var serverPort by rememberSaveable {
        mutableStateOf(
            preferences.getString("server_port", "8765") ?: "8765"
        )
    }

    var authToken by remember {
        mutableStateOf(
            AuthStorage.getToken(context)
        )
    }

    var showSettings by rememberSaveable {
        mutableStateOf(serverIp.isBlank())
    }

    LaunchedEffect(serverIp, serverPort, authToken)
    {
        if (serverIp.isNotBlank() && authToken.isNotBlank())
        {
            PairingClient.syncDeviceName(
                serverIp,
                serverPort,
                authToken
            )
        }
    }

    if (showSettings)
    {
        SettingsScreen(
            currentIp = serverIp,
            currentPort = serverPort,
            currentAuthToken = authToken,
            onSave = { ip, port, token ->
                val oldIp = serverIp

                serverIp = ip.trim()
                serverPort = port.trim()

                preferences.edit()
                    .putString("server_ip", serverIp)
                    .putString("server_port", serverPort)
                    .apply()

                if (token.isNotBlank())
                {
                    AuthStorage.saveToken(context, token)
                    authToken = token
                }
                else if (oldIp.isNotBlank() && oldIp != serverIp)
                {
                    AuthStorage.clearToken(context)
                    authToken = ""
                }

                showSettings = false
            },
            onCancel = {
                if (serverIp.isNotBlank())
                {
                    showSettings = false
                }
            },
            onDisconnect = {
                AuthStorage.clearToken(context)
                authToken = ""
                serverIp = ""
                serverPort = "8765"

                preferences.edit()
                    .remove("server_ip")
                    .putString("server_port", "8765")
                    .apply()

                showSettings = true
            },
            canCancel = serverIp.isNotBlank()
        )
    }
    else
    {
        DashboardScreen(
            serverIp = serverIp,
            serverPort = serverPort,
            authToken = authToken,
            onSettings = { showSettings = true }
        )
    }
}
