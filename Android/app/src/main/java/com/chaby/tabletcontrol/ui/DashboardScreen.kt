package com.chaby.tabletcontrol.ui

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
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun DashboardScreen(
    serverIp: String,
    serverPort: String,
    authToken: String,
    onSettings: () -> Unit
)
{
    var connectionError by remember { mutableStateOf(false) }
    var retryCounter by remember { mutableIntStateOf(0) }

    val serverUrl = "http://$serverIp:$serverPort"

    Scaffold { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        )
        {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically
            )
            {
                Column(modifier = Modifier.weight(1f))
                {
                    Text(
                        text = "TabletControl",
                        style = MaterialTheme.typography.titleLarge
                    )

                    Text(
                        text = if (connectionError) "Offline" else serverIp,
                        style = MaterialTheme.typography.bodySmall,
                        color = if (connectionError)
                        {
                            MaterialTheme.colorScheme.error
                        }
                        else
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
                key(serverUrl, authToken, retryCounter)
                {
                    DashboardWebView(
                        url = serverUrl,
                        authToken = authToken,
                        onConnectionChanged = { hasError ->
                            connectionError = hasError
                        }
                    )
                }

                if (connectionError)
                {
                    Box(
                        modifier = Modifier.fillMaxSize(),
                        contentAlignment = Alignment.Center
                    )
                    {
                        Card(modifier = Modifier.padding(24.dp))
                        {
                            Column(
                                modifier = Modifier.padding(24.dp),
                                horizontalAlignment = Alignment.CenterHorizontally
                            )
                            {
                                Text(
                                    text = "PC unavailable",
                                    style = MaterialTheme.typography.headlineSmall
                                )

                                Spacer(modifier = Modifier.height(8.dp))

                                Text("$serverIp:$serverPort")

                                Spacer(modifier = Modifier.height(20.dp))

                                Row(
                                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                                )
                                {
                                    OutlinedButton(onClick = onSettings)
                                    {
                                        Text("Settings")
                                    }

                                    Button(
                                        onClick = {
                                            connectionError = false
                                            retryCounter++
                                        }
                                    )
                                    {
                                        Text("Retry")
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