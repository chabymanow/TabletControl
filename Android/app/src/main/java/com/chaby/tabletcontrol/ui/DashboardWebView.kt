package com.chaby.tabletcontrol.ui

import android.annotation.SuppressLint
import android.graphics.Bitmap
import android.view.ViewGroup
import android.webkit.CookieManager
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView

private const val SESSION_COOKIE_NAME = "tabletcontrol_session"

@SuppressLint("SetJavaScriptEnabled")
@Composable
fun DashboardWebView(
    url: String,
    authToken: String,
    onConnectionChanged: (Boolean) -> Unit
)
{
    AndroidView(
        modifier = Modifier.fillMaxSize(),

        factory = { context ->
            WebView(context).apply {
                layoutParams = ViewGroup.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.MATCH_PARENT
                )

                settings.javaScriptEnabled = true
                settings.domStorageEnabled = true
                settings.loadsImagesAutomatically = true

                webViewClient = object : WebViewClient()
                {
                    private var mainFrameFailed = false

                    override fun onPageStarted(
                        view: WebView?,
                        url: String?,
                        favicon: Bitmap?
                    )
                    {
                        mainFrameFailed = false
                    }

                    override fun onReceivedError(
                        view: WebView?,
                        request: WebResourceRequest?,
                        error: WebResourceError?
                    )
                    {
                        if (request?.isForMainFrame == true)
                        {
                            mainFrameFailed = true
                            onConnectionChanged(true)
                        }
                    }

                    override fun onPageFinished(
                        view: WebView?,
                        url: String?
                    )
                    {
                        if (!mainFrameFailed)
                        {
                            onConnectionChanged(false)
                        }
                    }
                }

                val cookieManager = CookieManager.getInstance()

                cookieManager.setAcceptCookie(true)
                cookieManager.setAcceptThirdPartyCookies(this, false)

                if (authToken.isNotBlank())
                {
                    cookieManager.setCookie(
                        url,
                        "$SESSION_COOKIE_NAME=$authToken; Path=/; HttpOnly; SameSite=Strict"
                    ) {
                        cookieManager.flush()
                        loadUrl(url)
                    }
                }
                else
                {
                    cookieManager.setCookie(
                        url,
                        "$SESSION_COOKIE_NAME=; Path=/; Max-Age=0"
                    ) {
                        cookieManager.flush()
                        loadUrl(url)
                    }
                }
            }
        }
    )
}