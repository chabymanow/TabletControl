package com.chaby.tabletcontrol

import android.annotation.SuppressLint
import android.os.Bundle
import android.view.ViewGroup
import android.view.WindowManager
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import android.content.Context

import com.chaby.tabletcontrol.ui.theme.TabletControlTheme


class MainActivity : ComponentActivity()
{
    override fun onCreate(savedInstanceState: Bundle?)
    {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        setContent {TabletControlTheme {DashboardApp()}
        }
    }
}


@Composable
fun DashboardApp()
{
    val context = LocalContext.current

    val preferences =  remember {context.getSharedPreferences(
        "dashboard_settings",
        Context.MODE_PRIVATE
    )
    }

    var serverIp by rememberSaveable {mutableStateOf(
        preferences.getString(
            "server_ip",
            ""
        ) ?: ""
    )
    }

    var serverPort by rememberSaveable {mutableStateOf(
        preferences.getString(
            "server_port",
            "8765"
        ) ?: "8765"
    )
    }

    var showSettings by rememberSaveable {mutableStateOf(
        serverIp.isBlank()
    )
    }

    if (showSettings)
    {
        SettingsScreen(currentIp = serverIp, currentPort = serverPort,
            onSave = {ip,port -> serverIp = ip.trim()
                serverPort = port.trim()
                preferences.edit().putString("server_ip", serverIp).putString("server_port", serverPort).apply()
                showSettings = false
            },

            onCancel = {
                if (serverIp.isNotBlank())
                {
                    showSettings = false
                }
            },
            canCancel = serverIp.isNotBlank()
        )
    }
    else
    {
        DashboardScreen(serverIp = serverIp, serverPort = serverPort,
            onSettings = {showSettings = true}
        )
    }
}

@Composable
fun SettingsScreen(
    currentIp: String,
    currentPort: String,
    onSave: (String, String) -> Unit,
    onCancel: () -> Unit,
    canCancel: Boolean
)
{
    var ip by rememberSaveable {mutableStateOf(currentIp)}
    var port by rememberSaveable {mutableStateOf(currentPort)}
    var error by rememberSaveable {mutableStateOf("")}

    Scaffold { padding -> Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(padding)
            .padding(24.dp),

        contentAlignment = Alignment.Center
    )
    {
        Card(modifier = Modifier.fillMaxWidth())
        {
            Column(modifier = Modifier.padding(24.dp),
                verticalArrangement = Arrangement.spacedBy(18.dp)
            )
            {
                Text(text = "Dashboard Settings",
                    style = MaterialTheme.typography.headlineMedium
                )
                Text(text = "Enter the local IP address of your PC.")
                OutlinedTextField(
                    value = ip,
                    onValueChange = {ip = it},
                    label = {Text("PC IP address")},
                    placeholder = {Text("192.168.1.100")},
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                OutlinedTextField(
                    value = port,
                    onValueChange = {
                        port = it.filter {character -> character.isDigit()}
                    },
                    label = {Text("Port")},
                    placeholder = {Text("8765")},
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                if (error.isNotBlank())
                {
                    Text(text = error,
                        color = MaterialTheme.colorScheme.error
                    )
                }

                Row(modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                )
                {
                    if (canCancel)
                    {
                        OutlinedButton(onClick = onCancel, modifier = Modifier.weight(1f))
                        {
                            Text("Cancel")
                        }
                    }

                    Button(onClick = {val cleanIp = ip.trim()
                        val cleanPort =  port.trim().toIntOrNull()
                        if (cleanIp.isBlank())
                        {
                            error = "Please enter the PC IP address."
                            return@Button
                        }

                        if (
                            cleanPort == null || cleanPort !in 1..65535
                        )
                        {
                            error = "Please enter a valid port."
                            return@Button
                        }

                        error = ""
                        onSave(cleanIp, cleanPort.toString())
                    },

                        modifier = Modifier.weight(1f)
                    )
                    {
                        Text("Save")
                    }
                }
            }
        }
    }
    }
}


@Composable
fun DashboardScreen(
    serverIp: String,
    serverPort: String,
    onSettings: () -> Unit
)
{
    var connectionError by remember {
        mutableStateOf(
            false
        )
    }

    var retryCounter by remember {
        mutableIntStateOf(
            0
        )
    }
    val serverUrl = "http://$serverIp:$serverPort"
    Scaffold { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding))
        {
            Row(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically
            )
            {
                Column(modifier = Modifier.weight(1f))
                {
                    Text(text = "CachyOS", style = MaterialTheme.typography.titleLarge)

                    Text(text = if (connectionError)
                    {
                        "Offline"
                    }else
                    {
                        serverIp
                    },

                        style = MaterialTheme.typography.bodySmall,

                        color =if (connectionError)
                        {
                            MaterialTheme.colorScheme.error
                        }else
                        {
                            MaterialTheme.colorScheme.onSurfaceVariant
                        }
                    )
                }

                OutlinedButton(onClick = onSettings)
                {
                    Text("Settings")
                }
            }

            Box(modifier = Modifier.fillMaxSize())
            {
                key(serverUrl, retryCounter)
                {
                    DashboardWebView(url = serverUrl,
                        onConnectionChanged = {
                                hasError -> connectionError = hasError
                        }
                    )
                }

                if (connectionError)
                {
                    Box(
                        modifier =
                            Modifier
                                .fillMaxSize(),

                        contentAlignment =
                            Alignment.Center
                    )
                    {
                        Card(
                            modifier =
                                Modifier
                                    .padding(24.dp)
                        )
                        {
                            Column(
                                modifier =
                                    Modifier
                                        .padding(24.dp),

                                horizontalAlignment =
                                    Alignment.CenterHorizontally
                            )
                            {
                                Text(
                                    text =
                                        "PC unavailable",

                                    style =
                                        MaterialTheme
                                            .typography
                                            .headlineSmall
                                )

                                Spacer(
                                    modifier =
                                        Modifier
                                            .height(8.dp)
                                )

                                Text(
                                    text =
                                        "$serverIp:$serverPort"
                                )

                                Spacer(
                                    modifier =
                                        Modifier
                                            .height(20.dp)
                                )

                                Row(
                                    horizontalArrangement =
                                        Arrangement.spacedBy(
                                            12.dp
                                        )
                                )
                                {
                                    OutlinedButton(
                                        onClick =
                                            onSettings
                                    )
                                    {
                                        Text(
                                            "Settings"
                                        )
                                    }

                                    Button(
                                        onClick = {
                                            connectionError =
                                                false

                                            retryCounter++
                                        }
                                    )
                                    {
                                        Text(
                                            "Retry"
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}


@SuppressLint(
    "SetJavaScriptEnabled"
)
@Composable
fun DashboardWebView(
    url: String,
    onConnectionChanged: (
        Boolean
    ) -> Unit
)
{
    AndroidView(
        modifier =
            Modifier
                .fillMaxSize(),

        factory = {
                context ->

            WebView(
                context
            ).apply {

                layoutParams =
                    ViewGroup.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.MATCH_PARENT
                    )

                settings.javaScriptEnabled = true

                settings.domStorageEnabled = true

                settings.loadsImagesAutomatically = true

                webViewClient =
                    object : WebViewClient()
                    {
                        override fun onPageFinished(
                            view: WebView?,
                            url: String?
                        )
                        {
                            onConnectionChanged(
                                false
                            )
                        }


                        override fun onReceivedError(
                            view: WebView?,
                            request: WebResourceRequest?,
                            error: WebResourceError?
                        )
                        {
                            if (
                                request?.isForMainFrame ==
                                true
                            )
                            {
                                onConnectionChanged(
                                    true
                                )
                            }
                        }
                    }

                loadUrl(
                    url
                )
            }
        }
    )
}