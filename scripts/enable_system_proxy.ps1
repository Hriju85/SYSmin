param(
    [Parameter(Mandatory=$true)]
    [string]$ProxyServer # e.g. "127.0.0.1:8080" or "socks=127.0.0.1:9050"
)

Write-Host "Configuring Windows System Proxy to $ProxyServer..." -ForegroundColor Cyan

$regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
Set-ItemProperty -Path $regPath -Name ProxyEnable -Value 1
Set-ItemProperty -Path $regPath -Name ProxyServer -Value $ProxyServer

# Notify the system to refresh internet settings
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class WinINet {
    [DllImport("wininet.dll", SetLastError = true)]
    public static extern bool InternetSetOption(IntPtr hInternet, int dwOption, IntPtr lpBuffer, int dwBufferLength);
}
"@
[WinINet]::InternetSetOption([IntPtr]::Zero, 39, [IntPtr]::Zero, 0) # INTERNET_OPTION_SETTINGS_CHANGED
[WinINet]::InternetSetOption([IntPtr]::Zero, 37, [IntPtr]::Zero, 0) # INTERNET_OPTION_REFRESH

Write-Host "System Proxy ENABLED for $ProxyServer" -ForegroundColor Green
Write-Host "Run .\scripts\check_my_ip.ps1 to verify your masked IP." -ForegroundColor Yellow

