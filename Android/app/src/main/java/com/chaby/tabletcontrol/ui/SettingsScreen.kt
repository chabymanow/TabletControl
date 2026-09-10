package com.chaby.tabletcontrol.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.chaby.tabletcontrol.network.PairingClient
import kotlinx.coroutines.launch

@Composable
fun SettingsScreen(
    currentIp: String,
    currentPort: String,
    currentAuthToken: String,
    onSave: (String, String, String) -> Unit,
    onCancel: () -> Unit,
    onDisconnect: () -> Unit,
    canCancel: Boolean
)
{
    var ip by rememberSaveable { mutableStateOf(currentIp) }
    var port by rememberSaveable { mutableStateOf(currentPort) }
    var pairingCode by rememberSaveable { mutableStateOf("") }

    var error by rememberSaveable { mutableStateOf("") }
    var pairingMode by rememberSaveable { mutableStateOf(false) }
    var showDisconnectConfirmation by rememberSaveable { mutableStateOf(false) }
    var showLocalDisconnectConfirmation by rememberSaveable { mutableStateOf(false) }

    var isConnecting by rememberSaveable { mutableStateOf(false) }
    var isPairing by rememberSaveable { mutableStateOf(false) }
    var isDisconnecting by rememberSaveable { mutableStateOf(false) }

    val coroutineScope = rememberCoroutineScope()

    if (showDisconnectConfirmation)
    {
        AlertDialog(
            onDismissRequest = { showDisconnectConfirmation = false },
            title = { Text("Disconnect from PC?") },
            text = {
                Text(
                    "This removes this tablet from the PC's paired device list and clears the saved connection on this tablet."
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        showDisconnectConfirmation = false
                        error = ""
                        isDisconnecting = true

                        coroutineScope.launch {
                            val result = PairingClient.disconnect(
                                currentIp,
                                currentPort,
                                currentAuthToken
                            )

                            isDisconnecting = false

                            if (result.success)
                            {
                                onDisconnect()
                            }
                            else
                            {
                                error = result.message
                                showLocalDisconnectConfirmation = true
                            }
                        }
                    }
                )
                {
                    Text("Disconnect")
                }
            },
            dismissButton = {
                TextButton(onClick = { showDisconnectConfirmation = false })
                {
                    Text("Cancel")
                }
            }
        )
    }

    if (showLocalDisconnectConfirmation)
    {
        AlertDialog(
            onDismissRequest = { showLocalDisconnectConfirmation = false },
            title = { Text("PC could not be reached") },
            text = {
                Text(
                    "TabletControl could not remove this tablet from the PC. Disconnect locally anyway? The PC may still show this tablet as paired."
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        showLocalDisconnectConfirmation = false
                        onDisconnect()
                    }
                )
                {
                    Text("Disconnect locally")
                }
            },
            dismissButton = {
                TextButton(onClick = { showLocalDisconnectConfirmation = false })
                {
                    Text("Keep connection")
                }
            }
        )
    }

    Scaffold { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(24.dp),
            contentAlignment = Alignment.Center
        )
        {
            Card(modifier = Modifier.fillMaxWidth())
            {
                Column(
                    modifier = Modifier.padding(24.dp),
                    verticalArrangement = Arrangement.spacedBy(18.dp)
                )
                {
                    Text(
                        text = "TabletControl Settings",
                        style = MaterialTheme.typography.headlineMedium
                    )

                    Text("Connect this tablet to a PC running TabletControl.")

                    OutlinedTextField(
                        value = ip,
                        onValueChange = {
                            ip = it
                            error = ""
                            pairingMode = false
                        },
                        label = { Text("PC IP address") },
                        placeholder = { Text("192.168.1.100") },
                        singleLine = true,
                        enabled = !isConnecting && !isPairing && !isDisconnecting,
                        modifier = Modifier.fillMaxWidth()
                    )

                    OutlinedTextField(
                        value = port,
                        onValueChange = {
                            port = it.filter { character -> character.isDigit() }
                            error = ""
                            pairingMode = false
                        },
                        label = { Text("Port") },
                        placeholder = { Text("8765") },
                        singleLine = true,
                        enabled = !isConnecting && !isPairing && !isDisconnecting,
                        modifier = Modifier.fillMaxWidth()
                    )

                    if (pairingMode)
                    {
                        Text(
                            text = "Pairing is active on this PC.",
                            style = MaterialTheme.typography.titleMedium
                        )

                        Text("Enter the 6-digit pairing code displayed on the PC.")

                        OutlinedTextField(
                            value = pairingCode,
                            onValueChange = {
                                pairingCode = it
                                    .filter { character -> character.isDigit() }
                                    .take(6)

                                error = ""
                            },
                            label = { Text("Pairing code") },
                            placeholder = { Text("123456") },
                            singleLine = true,
                            enabled = !isPairing && !isDisconnecting,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }

                    if (isConnecting || isPairing || isDisconnecting)
                    {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(12.dp)
                        )
                        {
                            CircularProgressIndicator()

                            Text(
                                when
                                {
                                    isPairing -> "Pairing with TabletControl..."
                                    isDisconnecting -> "Disconnecting from TabletControl..."
                                    else -> "Connecting to TabletControl..."
                                }
                            )
                        }
                    }

                    if (error.isNotBlank())
                    {
                        Text(
                            text = error,
                            color = MaterialTheme.colorScheme.error
                        )
                    }

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    )
                    {
                        if (canCancel)
                        {
                            OutlinedButton(
                                onClick = onCancel,
                                enabled = !isConnecting && !isPairing && !isDisconnecting,
                                modifier = Modifier.weight(1f)
                            )
                            {
                                Text("Cancel")
                            }
                        }

                        if (pairingMode)
                        {
                            Button(
                                onClick = {
                                    val cleanIp = ip.trim()
                                    val cleanPort = port.trim()
                                    val cleanCode = pairingCode.trim()

                                    if (cleanCode.length != 6)
                                    {
                                        error = "Please enter the 6-digit pairing code."
                                        return@Button
                                    }

                                    error = ""
                                    isPairing = true

                                    coroutineScope.launch {
                                        val result = PairingClient.pair(
                                            cleanIp,
                                            cleanPort,
                                            cleanCode
                                        )

                                        isPairing = false

                                        if (result.success)
                                        {
                                            onSave(cleanIp, cleanPort, result.token)
                                        }
                                        else
                                        {
                                            error = result.message
                                        }
                                    }
                                },
                                enabled = !isPairing && !isDisconnecting && pairingCode.length == 6,
                                modifier = Modifier.weight(1f)
                            )
                            {
                                Text("Pair")
                            }
                        }
                        else
                        {
                            Button(
                                onClick = {
                                    val cleanIp = ip.trim()
                                    val cleanPort = port.trim().toIntOrNull()

                                    if (cleanIp.isBlank())
                                    {
                                        error = "Please enter the PC IP address."
                                        return@Button
                                    }

                                    if (cleanPort == null || cleanPort !in 1..65535)
                                    {
                                        error = "Please enter a valid port."
                                        return@Button
                                    }

                                    error = ""
                                    isConnecting = true

                                    coroutineScope.launch {
                                        val status = PairingClient.getStatus(
                                            cleanIp,
                                            cleanPort.toString()
                                        )

                                        isConnecting = false

                                        if (!status.success)
                                        {
                                            error = status.message
                                            return@launch
                                        }

                                        if (status.pairingActive)
                                        {
                                            pairingMode = true
                                            return@launch
                                        }

                                        if (status.authenticationRequired)
                                        {
                                            error = "This PC requires pairing. Start pairing on the PC first."
                                            return@launch
                                        }

                                        onSave(cleanIp, cleanPort.toString(), "")
                                    }
                                },
                                enabled = !isConnecting && !isDisconnecting,
                                modifier = Modifier.weight(1f)
                            )
                            {
                                Text("Connect")
                            }
                        }
                    }

                    if (canCancel)
                    {
                        OutlinedButton(
                            onClick = { showDisconnectConfirmation = true },
                            enabled = !isConnecting && !isPairing && !isDisconnecting,
                            modifier = Modifier.fillMaxWidth()
                        )
                        {
                            Text("Disconnect from PC")
                        }
                    }
                }
            }
        }
    }
}
