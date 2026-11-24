# The launcher's updater and first-run setup (T113), dot-sourced by play_mods.ps1. Functions only; the selftest is update_selftest.ps1.
# Windows PowerShell 5.1, ASCII only (5.1 reads a file with no BOM in the PC's code page).
#
# A release of the public repo (KDMSENSOR) carries manifest.json (version, parts, every file's SHA-256) and one zip per part.
# An update downloads only the parts whose SHA-256 changed, checks size and SHA-256 of each zip and of every extracted file in a
# staging folder (mods\update), and only then replaces the files, with a backup it puts back on any failure: a download that fails
# or is cut short leaves the working version as it was. It writes only what the manifest lists, and only under 1 - Play.bat,
# 1 - Play (README).txt and mods\ (never modules\, data\, prop\, arkdata\, nor the player's settings, saves and generated content).
#
# First-run setup: the content a Konami base cannot give (the restored audio, one archive for ever, SHA-256 checked; the player puts it
# in mods\, the repo never links it) is extracted into mods\, then mods\generator (its own Python) makes the rest from the player's own game files and checks every file
# against mods\generated.json before writing any of them.

$script:KdmRepo = "Cris-Oblea/KDMSENSOR"
# what an update may write: the launcher and its readme, and mods\ except the player's and the generated content
$script:KdmOwned = '^(1 - Play\.bat|1 - Play \(README\)\.txt|mods/(?!(data|conf|active|snd|reports|update|fixed)/|selection\.json|setup\.json|version\.json|generated\.state)[^\\:*?"<>|]+)$'
Add-Type -AssemblyName System.IO.Compression.FileSystem
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch { }

# .NET, not Get-FileHash: that cmdlet needs a module a broken PSModulePath hides (play_mods.ps1 Md5)
function KdmSha($f) { $h = [Security.Cryptography.SHA256]::Create(); $s = [IO.File]::OpenRead($f); try { ([BitConverter]::ToString($h.ComputeHash($s)) -replace "-", "").ToLowerInvariant() } finally { $s.Dispose() } }
function KdmJson($f) { Get-Content -LiteralPath $f -Raw -Encoding UTF8 | ConvertFrom-Json }
function KdmDoEvents { try { [Windows.Forms.Application]::DoEvents() } catch { } }

# One file from a URL (https) or a local path (the selftest).
# Waits with the window answering; gives up when nothing arrives for $idle seconds.
function KdmGet($src, $dst, [scriptblock]$tick, [int]$idle = 30) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
    if ($src -notmatch '^https?://') { Copy-Item -LiteralPath $src -Destination $dst -Force; return }
    $wc = New-Object Net.WebClient
    $wc.Headers["User-Agent"] = "KDMSENSOR-launcher"
    try {
        $t = $wc.DownloadFileTaskAsync($src, $dst)
        $last = 0; $seen = Get-Date
        while (-not $t.IsCompleted) {
            KdmDoEvents; Start-Sleep -Milliseconds 60
            $n = if (Test-Path -LiteralPath $dst) { (Get-Item -LiteralPath $dst).Length } else { 0 }
            if ($n -ne $last) { $last = $n; $seen = Get-Date }
            elseif (((Get-Date) - $seen).TotalSeconds -gt $idle) { $wc.CancelAsync(); throw "no data from $src for $idle seconds" }
            if ($tick) { & $tick $n }
        }
        if ($t.IsFaulted) { throw $t.Exception.InnerException.Message }
        if ($t.IsCanceled) { throw "download cancelled" }
    } finally { $wc.Dispose() }
    if (-not (Test-Path -LiteralPath $dst)) { throw "nothing downloaded from $src" }
}

# The installed version, or $null when this folder is not a release install (the project's own folder has none: nothing to update).
function Get-KdmInstalled($mods) {
    $f = Join-Path $mods "version.json"
    if (Test-Path -LiteralPath $f) { try { KdmJson $f } catch { $null } } else { $null }
}

# The newest release as { version; name; body; assets = name -> url }, or $null when it cannot be read (offline, no release yet).
# $src: the GitHub API's releases/latest URL, or a local release.json (same shape, the selftest's).
function Get-KdmRelease($src, $work, [int]$seconds = 10) {
    if (-not $src) { $src = "https://api.github.com/repos/$script:KdmRepo/releases/latest" }
    try {
        $f = Join-Path $work "release.json"
        KdmGet $src $f $null $seconds
        $j = KdmJson $f
        $a = @{}; foreach ($x in $j.assets) { $a[[string]$x.name] = [string]$x.browser_download_url }
        [pscustomobject]@{ version = [version](([string]$j.tag_name).TrimStart("v")); name = [string]$j.name; body = [string]$j.body; assets = $a }
    } catch { $script:KdmWhy = if ("$_" -match '\(404\)') { "none" } else { "offline" }; $null } finally { Remove-Item -LiteralPath (Join-Path $work "release.json") -Force -ErrorAction SilentlyContinue }
}

# The check the opening and the launcher's button share: { status = newer | current | offline | none; rel; text }, text being the status line.
# GitHub answers 404 to releases/latest while the repo has no release; any other failure is the internet (or an unreadable answer).
function Find-KdmUpdate($installed, $src, $work, [int]$seconds = 10) {
    $script:KdmWhy = "offline"
    $rel = Get-KdmRelease $src $work $seconds
    if (-not $rel) {
        if ($script:KdmWhy -eq "none") { return [pscustomobject]@{ status = "none"; rel = $null; text = "No release published yet: you have version $($installed.version)" } }
        return [pscustomobject]@{ status = "offline"; rel = $null; text = "Could not look for updates (no internet?): you have version $($installed.version)" }
    }
    if ($rel.version -gt [version]$installed.version) { return [pscustomobject]@{ status = "newer"; rel = $rel; text = "Version $($rel.version) is available" } }
    [pscustomobject]@{ status = "current"; rel = $rel; text = "Up to date: version $($installed.version)" }
}

function KdmCheckPath($p) {
    if ($p -match '(^|/)\.\.(/|$)' -or $p -notmatch $script:KdmOwned) { throw "the release lists a file this launcher never writes: $p" }
}

# Replaces the files of the parts that changed. Throws, with every file as it was, on any failure.
function Install-KdmUpdate($root, $rel, [scriptblock]$say) {
    $mods = Join-Path $root "mods"
    $have = Get-KdmInstalled $mods
    $work = Join-Path $mods "update"
    Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue   # what an earlier cut-short try left
    $dir = Join-Path $work $rel.version.ToString()
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    try {
        if ($say) { & $say "Reading the release..." }
        if (-not $rel.assets.ContainsKey("manifest.json")) { throw "the release has no manifest.json" }
        KdmGet $rel.assets["manifest.json"] (Join-Path $dir "manifest.json")
        $man = KdmJson (Join-Path $dir "manifest.json")
        if ([version]$man.version -ne $rel.version) { throw "the manifest is for version $($man.version), not $($rel.version)" }
        foreach ($p in $man.parts) { foreach ($f in $p.files) { KdmCheckPath $f.path } }
        # 1. download and check every changed part, whole, before anything is touched
        $stage = Join-Path $dir "stage"
        foreach ($p in $man.parts) {
            $same = $have -and $have.parts -and ($have.parts.PSObject.Properties[$p.name]) -and $have.parts.($p.name) -eq $p.sha256 -and
                    -not (@($p.files | Where-Object { -not (Test-Path -LiteralPath (Join-Path $root $_.path)) }).Count)
            if ($same) { continue }
            if (-not $rel.assets.ContainsKey($p.zip)) { throw "the release has no $($p.zip)" }
            $zip = Join-Path $dir $p.zip
            KdmGet $rel.assets[$p.zip] $zip { param($n) if ($say) { & $say ("Downloading {0}: {1:N1} of {2:N1} MB" -f $p.name, ($n / 1MB), ($p.size / 1MB)) } }
            if ((Get-Item -LiteralPath $zip).Length -ne $p.size) { throw "$($p.zip) is incomplete ($((Get-Item -LiteralPath $zip).Length) of $($p.size) bytes)" }
            if ((KdmSha $zip) -ne $p.sha256) { throw "$($p.zip) does not match its SHA-256" }
            if ($say) { & $say "Unpacking $($p.name)..." }
            [IO.Compression.ZipFile]::ExtractToDirectory($zip, (Join-Path $stage $p.name))
            Remove-Item -LiteralPath $zip -Force
            foreach ($f in $p.files) {
                $x = Join-Path (Join-Path $stage $p.name) $f.path
                if (-not (Test-Path -LiteralPath $x) -or (KdmSha $x) -ne $f.sha256) { throw "$($f.path) in $($p.zip) does not match the manifest" }
            }
        }
        # 2. replace, keeping every old file to put back
        if ($say) { & $say "Installing..." }
        $backup = Join-Path $dir "backup"
        $done = New-Object Collections.ArrayList   # @{ path; had } in the order done
        $newFiles = @{}
        foreach ($p in $man.parts) { foreach ($f in $p.files) { $newFiles[$f.path] = $true } }
        try {
            foreach ($p in $man.parts) {
                if (-not (Test-Path -LiteralPath (Join-Path $stage $p.name))) { continue }   # unchanged part
                foreach ($f in $p.files) {
                    $dst = Join-Path $root $f.path
                    $had = Test-Path -LiteralPath $dst
                    if ($had) { $b = Join-Path $backup $f.path; New-Item -ItemType Directory -Force -Path (Split-Path -Parent $b) | Out-Null; Copy-Item -LiteralPath $dst -Destination $b -Force }
                    [void]$done.Add(@{ path = $dst; had = $had; rel = $f.path })
                    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
                    Copy-Item -LiteralPath (Join-Path (Join-Path $stage $p.name) $f.path) -Destination $dst -Force
                }
            }
            if ($have -and $have.files) {   # a file the old version had and the new one does not
                foreach ($o in $have.files.PSObject.Properties.Name) {
                    $dst = Join-Path $root $o
                    if (-not $newFiles.ContainsKey($o) -and ($o -match $script:KdmOwned) -and (Test-Path -LiteralPath $dst)) {
                        $b = Join-Path $backup $o; New-Item -ItemType Directory -Force -Path (Split-Path -Parent $b) | Out-Null; Copy-Item -LiteralPath $dst -Destination $b -Force
                        [void]$done.Add(@{ path = $dst; had = $true; rel = $o })
                        Remove-Item -LiteralPath $dst -Force
                    }
                }
            }
            $files = [ordered]@{}; $parts = [ordered]@{}
            foreach ($p in $man.parts) { $parts[$p.name] = $p.sha256; foreach ($f in $p.files) { $files[$f.path] = $f.sha256 } }
            $vj = Join-Path $mods "version.json"
            ([ordered]@{ version = $rel.version.ToString(); parts = $parts; files = $files } | ConvertTo-Json -Depth 4) | Set-Content -LiteralPath ($vj + ".new") -Encoding UTF8
            Move-Item -LiteralPath ($vj + ".new") -Destination $vj -Force
        } catch {
            $why = $_
            for ($i = $done.Count - 1; $i -ge 0; $i--) {
                $d = $done[$i]
                if ($d.had) { Copy-Item -LiteralPath (Join-Path $backup $d.rel) -Destination $d.path -Force } else { Remove-Item -LiteralPath $d.path -Force -ErrorAction SilentlyContinue }
            }
            throw $why
        }
    } finally { Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue }
}

# What the first run (and a new fixed archive or generated.json) needs. Returns $null when there is nothing to do or it worked, the
# problem as one sentence when it did not. Inert in a folder with no mods\generator (the project's own).
function Initialize-KdmContent($root, [scriptblock]$say) {
    $mods = Join-Path $root "mods"
    $gen = Join-Path $mods "generator"
    if (-not (Test-Path -LiteralPath $gen)) { return $null }
    $stateFile = Join-Path $mods "setup.json"
    $st = @{ fixed = ""; generated = "" }
    if (Test-Path -LiteralPath $stateFile) { try { $j = KdmJson $stateFile; $st.fixed = [string]$j.fixed; $st.generated = [string]$j.generated } catch { } }
    $work = Join-Path $mods "update"
    try {
        $fx = KdmJson (Join-Path $mods "fixed.json")
        $expectSha = KdmSha (Join-Path $mods "generated.json")
        if ($st.fixed -ne $fx.sha256) {
            $arc = Join-Path $mods $fx.name   # the player puts it there; where it is shared is never said here (the repo is public)
            $mb = [int]($fx.size / 1MB)
            if (-not (Test-Path -LiteralPath $arc)) { return "One more file is needed, once: $($fx.name) (about $mb MB, the songs' restored audio). Put it, with that name, in this folder:`r`n$mods`r`nthen open the launcher again." }
            if ((Get-Item -LiteralPath $arc).Length -ne $fx.size -or (KdmSha $arc) -ne $fx.sha256) {
                return "$($fx.name) in $mods is incomplete or not the file this version expects (size or SHA-256). Get it again and replace it."
            }
            if ($say) { & $say "Unpacking the restored audio..." }
            $p = Start-Process -FilePath (Join-Path $mods "bin\7zr.exe") -ArgumentList ('x -y -bso0 -bsp0 -o"{0}" "{1}"' -f $mods, $arc) -Wait -PassThru -WindowStyle Hidden
            if ($p.ExitCode) { return "Could not unpack $($fx.name) (7zr exit code $($p.ExitCode))." }
            $st.fixed = $fx.sha256; $st.generated = ""
        }
        if ($st.generated -ne ($expectSha + $st.fixed)) {
            if ($say) { & $say "Making the mods from your game files (first time, about a minute)..." }
            $log = Join-Path $work "generator.log"
            New-Item -ItemType Directory -Force -Path $work | Out-Null
            $psi = @{ FilePath = (Join-Path $mods "bin\python\python.exe"); ArgumentList = ('-B "{0}" --make "{1}"' -f (Join-Path $gen "regen_pack.py"), (Join-Path $mods "generated.json"))
                      WorkingDirectory = $root; RedirectStandardOutput = $log; RedirectStandardError = ($log + ".err"); PassThru = $true; WindowStyle = "Hidden" }
            $p = Start-Process @psi
            $null = $p.Handle   # without the handle taken at once, ExitCode of a -PassThru process reads $null (the known Start-Process trap)
            while (-not $p.HasExited) { KdmDoEvents; Start-Sleep -Milliseconds 100 }
            $p.WaitForExit()
            if ($p.ExitCode -ne 0 -or -not (Test-Path -LiteralPath (Join-Path $mods "generated.state"))) {
                $out = (@(Get-Content -LiteralPath $log -ErrorAction SilentlyContinue) + @(Get-Content -LiteralPath ($log + ".err") -ErrorAction SilentlyContinue) | Select-Object -Last 4) -join " "
                return "Could not make the mods from your game files: $out"
            }
            $st.generated = $expectSha + $st.fixed
        }
        ([ordered]@{ fixed = $st.fixed; generated = $st.generated } | ConvertTo-Json) | Set-Content -LiteralPath $stateFile -Encoding UTF8
        return $null
    } catch { return "Setup failed: $_" } finally { Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue }
}

# The window that tells what changed: Update or Not now. Returns $true for Update.
function Show-KdmUpdate($installed, $rel) {
    $f = New-Object Windows.Forms.Form -Property @{ Text = "DanceEvolution ARCADE: update"; StartPosition = "CenterScreen"; FormBorderStyle = "FixedDialog"; MaximizeBox = $false; MinimizeBox = $false
        ClientSize = New-Object Drawing.Size(520, 380); Font = New-Object Drawing.Font("Segoe UI", 9) }
    $l = New-Object Windows.Forms.Label -Property @{ AutoSize = $false; Left = 14; Top = 12; Width = 490; Height = 36
        Text = "Version {0} is available (you have {1}). What changed:" -f $rel.version, $(if ($installed) { $installed.version } else { "none" }) }
    $t = New-Object Windows.Forms.TextBox -Property @{ Multiline = $true; ReadOnly = $true; ScrollBars = "Vertical"; Left = 14; Top = 52; Width = 490; Height = 264; Text = ($rel.body -replace "(?<!\r)\n", "`r`n") }
    $y = New-Object Windows.Forms.Button -Property @{ Text = "Update"; Left = 300; Top = 332; Width = 100; Height = 30; DialogResult = "Yes" }
    $n = New-Object Windows.Forms.Button -Property @{ Text = "Not now"; Left = 410; Top = 332; Width = 94; Height = 30; DialogResult = "No" }
    $f.Controls.AddRange(@($l, $t, $y, $n)); $f.AcceptButton = $y; $f.CancelButton = $n
    $r = $f.ShowDialog(); $f.Dispose()
    return ($r -eq "Yes")
}
