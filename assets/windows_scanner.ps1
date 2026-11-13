param([string]$Action, [string]$DeviceId, [int]$Dpi, [string]$Target)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
try {
    $console = @("$env:ProgramFiles/NAPS2/NAPS2.Console.exe",
                 "${env:ProgramFiles(x86)}/NAPS2/NAPS2.Console.exe") |
                 Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    $names = @()
    $diagnostics = @()
    $info = $null
    try {
        $manager = New-Object -ComObject WIA.DeviceManager
        $devices = $manager.DeviceInfos
        for ($i = 1; $i -le $devices.Count; $i++) {
            $candidate = $devices.Item($i)
            if ($candidate.Type -ne 1) { continue }
            $id = [string]$candidate.DeviceID
            $name = $id
            foreach ($property in $candidate.Properties) {
                if ($property.PropertyID -eq 7) { $name = [string]$property.Value; break }
            }
            $names += [pscustomobject]@{ id = $id; name = "$name (WIA)" }
            if ($id -eq $DeviceId) { $info = $candidate }
        }
    } catch { $diagnostics += "WIA: $($_.Exception.Message)" }
    if ($Action -eq 'list') {
        if ($console) {
            foreach ($driver in 'twain','escl') {
                try {
                    $lines = & $console --listdevices --driver $driver
                    if ($LASTEXITCODE -ne 0) { throw "Falha ao consultar $driver." }
                    foreach ($line in $lines) {
                        $name = $line.Trim()
                        if ($name) {
                            $names += [pscustomobject]@{ id = "naps/$driver/$name"; name = "$name ($driver)" }
                        }
                    }
                } catch { $diagnostics += $_.Exception.Message }
            }
        }
        if (!$names.Count) {
            $service = Get-Service -Name stisvc -ErrorAction SilentlyContinue
            if ($service) { $diagnostics += "Servico WIA: $($service.Status)." }
            $diagnostics += 'Confira se o scanner aparece em Impressoras e scanners do Windows e se o driver de digitalizacao do fabricante esta instalado.'
            if (!$console) { $diagnostics += 'Para consultar TWAIN e scanners de rede eSCL, instale o NAPS2.' }
        }
        ConvertTo-Json -InputObject @{ devices = $names; detail = ($diagnostics -join ' ') } -Depth 3 -Compress
        exit 0
    }
    if ($DeviceId.StartsWith('naps/')) {
        $parts = $DeviceId -split '/', 3
        $arguments = @('--noprofile','--driver',$parts[1],'--device',$parts[2],'-o',$Target)
        if ($Dpi) { $arguments += @('--dpi',"$Dpi") }
        if (!$console) { throw 'NAPS2 indisponivel.' }
        & $console @arguments | Out-Null
        if ($LASTEXITCODE -ne 0 -or !(Test-Path -LiteralPath $Target)) { throw 'Falha ao digitalizar com NAPS2. Confira o equipamento e a resolucao.' }
        Write-Output $Dpi
        exit 0
    }
    if (!$info) { throw 'Scanner desconectado. Atualize a lista.' }
    $device = $info.Connect()
    $item = $device.Items.Item(1)
    foreach ($id in 6147,6148) {
        $prop = $item.Properties | Where-Object { $_.PropertyID -eq $id }
        if (!$prop) { throw 'O driver nao informa a resolucao.' }
        if ($Dpi -and $prop.Value -ne $Dpi) { $prop.Value = $Dpi }
        if ($Dpi -and $prop.Value -ne $Dpi) { throw 'Resolucao nao aceita pelo scanner.' }
    }
    # Scan the whole bed at the selected resolution where the driver permits.
    foreach ($id in 6151,6152) {
        $extent = $item.Properties | Where-Object { $_.PropertyID -eq $id }
        if ($extent -and !$extent.IsReadOnly -and $extent.SubType -eq 1) {
            $extent.Value = $extent.SubTypeMax
        }
    }
    $image = $item.Transfer('{B96B3CAB-0728-11D3-9D7B-0000F81EF32E}')
    $image.SaveFile($Target)
    Write-Output ([int]$image.HorizontalResolution)
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
