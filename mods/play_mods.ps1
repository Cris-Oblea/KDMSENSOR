# The players' launcher ("1 - Play.bat"): one small window with every mod, the spice2x settings and
# Play. The game's own files are never written: the chosen code edits go into a COPY of
# modules\ and of spice.exe under mods\active\, the chosen data is served by the LayeredFS hook
# from mods\data\, and the rest is environment variables for our d3d9 proxy. With every option
# on its first value it is Konami's original game.
#
# Independent of whatever else is installed (other mods, the player's own launcher): its own spice2x from mods\bin, and
# its settings, patches, saves and log in mods\conf, all by spice2x's path options. It writes nothing outside mods\.
#
# mods\catalog.json (built by _tools/mods/build_mods.py) holds every option: what it does, what
# it needs, its edits (spice2x "memory" patches whose original bytes are checked) and its
# data folders. Choosing a value switches on what it needs; a value whose needs are switched
# off goes back to the original. The choice is saved at every change (mods\selection.json).
#
#   mods\play_mods.ps1                     the window
#   mods\play_mods.ps1 -Select "language=eng,songs=all" -NoLaunch
#                                          sets values and builds mods\active, no game
#
# Windows PowerShell 5.1 and WinForms on purpose: every player has them, nothing to install.
# Every path goes to the cmdlets as -LiteralPath: a game folder named "[KDM] ..." is a wildcard to them otherwise, and
# the launcher could not read its own files. The file stays ASCII: PowerShell 5.1 reads it in the PC's own code page.
param([string]$Select = "", [switch]$NoLaunch, [switch]$Elevated)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
# The window runs with no console: an error has to be shown, or the player sees nothing happen.
trap { if (-not $NoLaunch) { [void][Windows.Forms.MessageBox]::Show("$_", "DanceEvolution ARCADE") }; break }

# spice2x relaunches itself as administrator when it is not, and that relaunch gets a fresh environment: every
# option passed in a variable (the webcam's KDM_SENSOR, the picture's filters, full screen) was lost, the process
# Play started ended at once (the closing message came before the game), and the game came up behind the UAC
# prompt (2026-10-31). So the launcher asks once, when it opens; spice2x is then its child and inherits everything.
# By the group's SID, never its name: the group is "Administrators" only on an English Windows (a Russian one calls it by
# another name), IsInRole("Administrators") was false there even elevated, and the launcher relaunched itself hidden for
# ever: the prompt, then nothing (reported 2026-11-12). -Elevated marks the relaunch, so it can never happen twice.
function IsAdmin { ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator) }
if (-not $NoLaunch -and -not (IsAdmin)) {
    if ($Elevated) { throw "Windows did not give the launcher administrator rights, and the game (spice2x) needs them. Open it from an administrator account." }
    $me = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}" -Elevated' -f $PSCommandPath
    if ($Select) { $me += ' -Select "{0}"' -f $Select }
    try { Start-Process "$PSHOME\powershell.exe" -Verb RunAs -WindowStyle Hidden -ArgumentList $me }
    catch { [void][Windows.Forms.MessageBox]::Show("The game needs administrator rights (spice2x asks for them). Open the launcher again and choose Yes.", "DanceEvolution ARCADE") }
    exit 0
}
$mods = $PSScriptRoot
$root = Split-Path -Parent $mods
$active = Join-Path $mods "active"
$catPath = Join-Path $mods "catalog.json"
$selPath = Join-Path $mods "selection.json"
$cat = Get-Content -LiteralPath $catPath -Raw -Encoding UTF8 | ConvertFrom-Json
. (Join-Path $mods "update.ps1")   # the updater and the first-run setup (a release install only uses them)

function Opt($id) { $cat.options | Where-Object { $_.id -eq $id } }
function Val($oid, $vid) { (Opt $oid).values | Where-Object { $_.id -eq $vid } }
function Needs($v) { if ($v.PSObject.Properties["needs"]) { @($v.needs) } else { @() } }
# A "test" value is not verified in game yet: only -Select reaches it. An option left with its original alone is not
# listed, nor an "auto" one: it is part of the options that need it and follows them (sound memory, sound files...).
# A value with a "mode" (a resolution) is listed only if the main screen offers it: the game always runs in exclusive full screen.
function ScreenModes {
    if (-not $script:screenModes) {
        Add-Type -TypeDefinition @'
using System; using System.Collections.Generic; using System.Runtime.InteropServices;
public class KdmDisplay {
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)] struct DM {
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string name; public ushort spec, drv, size, extra; public uint fields; public int x, y; public uint orient, fixedOut;
        public short color, duplex, yres, tt, collate; [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string form; public ushort lp; public uint bpp, w, h, flags, hz;
        public uint icm, intent, media, dither, r1, r2, pw, ph; }
    [DllImport("user32", CharSet = CharSet.Unicode)] static extern bool EnumDisplaySettingsW(string dev, int mode, ref DM d);
    public static string[] Modes() {
        var s = new SortedSet<string>(); var m = new DM(); m.size = (ushort) Marshal.SizeOf(m);
        for (int i = 0; EnumDisplaySettingsW(null, i, ref m); i++) s.Add(m.w + "x" + m.h + "@" + m.hz);
        var a = new string[s.Count]; s.CopyTo(a); return a; }
}
'@
        $script:screenModes = [KdmDisplay]::Modes()
    }
    $script:screenModes
}
function Shown($o) {
    @($o.values | Where-Object { -not $_.PSObject.Properties["test"] } | Where-Object {
        -not $_.PSObject.Properties["mode"] -or @(ScreenModes) -like ("{0}x{1}@*" -f $_.mode[0], $_.mode[1]) })
}
$menu = @($cat.options | Where-Object { -not $_.auto -and (Shown $_).Count -gt 1 })

$sel = @{}
foreach ($o in $cat.options) { $sel[$o.id] = $o.values[0].id }
$camera = ""   # the webcam sensor's camera, by name (empty: the first one Windows lists)
# The virtual mount (WEBCAM_SENSOR.md section 5), on unless the player turns it off (the game's hand cursor has a 2 m sensor built in): off, the camera is the Kinect; on, the skeleton and the picture
# are re-expressed as a Kinect at (hv, tv) would see them, from the camera's real height, tilt and lens.
# The default Kinect (WEBCAM_SENSOR.md section 5): 2 m and -17, what the game's hand cursor points to and what the user plays.
$mount = [ordered]@{ on = $true; hr = 1.0; tr = 0.0; hfov = 70.0; hv = 2.0; tv = -17.0; cal = "" }   # cal: the date Calibrate camera... set it, empty when typed
# A selection cut short (the power went, the disk filled) must not keep the launcher from opening: the defaults instead.
$saved = try { Get-Content -LiteralPath $selPath -Raw -ErrorAction Stop | ConvertFrom-Json } catch { $null }
if ($saved) {
    foreach ($p in $saved.PSObject.Properties) { if (Val $p.Name $p.Value) { $sel[$p.Name] = $p.Value } }
    if ($saved.PSObject.Properties["camera"]) { $camera = [string]$saved.camera }
    if ($saved.PSObject.Properties["mount"]) { foreach ($k in @($mount.Keys)) { if ($saved.mount.PSObject.Properties[$k]) { $mount[$k] = $saved.mount.$k } } }
}
$sensorExe = Join-Path $mods "webcam\kdmsensor.exe"
# kdmsensor.exe's arguments for the chosen camera and placement
function SensorArgs {
    $a = '--camera "{0}"' -f $script:camera
    if ($script:mount.on) {
        $inv = [Globalization.CultureInfo]::InvariantCulture
        $a += " --mount " + ((@("hr", "tr", "hfov", "hv", "tv") | ForEach-Object { ([double]$script:mount[$_]).ToString($inv) }) -join ",")
    }
    $a + (SensorDevice)
}
# where RTMPose runs: the GPU (the default; kdmsensor falls back to the CPU when DirectML cannot load), or the CPU by hand
function SensorDevice { if ($script:sel["sensorload"] -eq "cpu") { "" } else { " --gpu" } }

# The calibrator (kdmsensor --calibrate, WEBCAM_SENSOR.md 4b), nothing typed: two still stances give the camera's height and tilt, both arms
# up check the picture's top, the right arm out at the shoulder sets the cursor's height (the song selector's band, read from the game), the
# arm up checks the OK, a crouch checks the game keeps the player; the game's Kinect is tilted to frame the feet to the raised hands; the GPU always. One confirmation saves it.
function Calibrate {
    if (-not (Test-Path -LiteralPath $sensorExe)) { [void][Windows.Forms.MessageBox]::Show("mods\webcam is missing.", "Calibrate camera"); return $false }
    $out = Join-Path $env:TEMP "kdm_calibration.txt"
    Remove-Item -LiteralPath $out -ErrorAction SilentlyContinue
    $inv = [Globalization.CultureInfo]::InvariantCulture
    $m = (@("hr", "tr", "hfov", "hv", "tv") | ForEach-Object { ([double]$script:mount[$_]).ToString($inv) }) -join ","
    $a = '--preview --calibrate --camera "{0}" --calib-out "{1}" --mount {2}' -f $script:camera, $out, $m
    $a += SensorDevice
    $psi = New-Object Diagnostics.ProcessStartInfo -Property @{ FileName = $sensorExe; Arguments = $a; UseShellExecute = $false; CreateNoWindow = $true }
    $p = [Diagnostics.Process]::Start($psi)
    while (-not $p.HasExited) { [Windows.Forms.Application]::DoEvents(); Start-Sleep -Milliseconds 100 }
    if (-not (Test-Path -LiteralPath $out)) { [void][Windows.Forms.MessageBox]::Show("The calibration was closed before it finished: nothing changed.", "Calibrate camera"); return $false }
    $r = @{}
    foreach ($line in Get-Content -LiteralPath $out) { $k, $v = $line -split "=", 2; if ($k) { $r[$k] = $v } }
    if ($r["ok"] -ne "1") { [void][Windows.Forms.MessageBox]::Show("The calibration could not finish: $($r['reason']). Nothing changed.", "Calibrate camera"); return $false }
    $tilt, $hv, $hr = [double]::Parse($r["tilt"], $inv), [double]::Parse($r["hv"], $inv), [double]::Parse($r["height"], $inv)
    $arms = if ($r["arms"] -eq "1") { "" } else { "`r`n`r`nYour raised hands left the picture: for songs, step back or tilt the camera up, then calibrate again." }
    if ($r["back"] -and [double]::Parse($r["back"], $inv) -gt 0) { $arms += "`r`n`r`nYour feet and raised hands do not both fit the game's picture: stand about {0:0.0} m farther back, then calibrate again." -f [double]::Parse($r["back"], $inv) }
    elseif ($r["handscut"] -eq "1") { $arms += "`r`n`r`nIn the songs that raise the hands highest they may leave the top of the game's picture for a moment; your feet stay in." }
    if ($r["side"] -and [double]::Parse($r["side"], $inv) -gt 0) { $arms += "`r`n`r`nWide moves may leave the picture at the sides: stand in the middle of it, or about {0:0.0} m farther back." -f (2 * [double]::Parse($r["side"], $inv)) }
    if ($r["twonarrow"] -eq "1") { $arms += "`r`n`r`nFor two players this camera's picture is too narrow here: one player fits." }
    elseif ($r["two"] -and [double]::Parse($r["two"], $inv) -gt 0) { $arms += "`r`n`r`nFor two players side by side, both stand about {0:0.0} m farther back." -f [double]::Parse($r["two"], $inv) }
    if ($r["effects"]) { $arms += "`r`n`r`nWindows could not turn off this camera's {0}: it changes the picture the game reads. Turn it off in Windows Settings > Bluetooth & devices > Cameras." -f $r["effects"] }
    # the player's height is not shown: it comes from an average body's bones and was 10 % short for the user, costing no grade (WEBCAM_SENSOR.md 3h)
    $q = "Camera: {0:0.00} m high, tilt {1:+0.0;-0.0} degrees.`r`nYou: {3} m away.`r`nHand cursor: set for your arm at shoulder height.`r`nThe game's Kinect: {5:0.00} m high, tilt {6}, your feet to your raised hands in its picture.`r`nPose model: on the GPU.{4}`r`n`r`nSave this calibration?" -f $hr, $tilt, $r["player"], $r["distance"], $arms, $hv, $r["tv"]
    if ([Windows.Forms.MessageBox]::Show($q, "Calibrate camera", "YesNo") -ne "Yes") { return $false }
    $script:mount.on = $true
    $script:mount.hr = [Math]::Round($hr, 2); $script:mount.tr = [Math]::Round($tilt, 1); $script:mount.hv = [Math]::Round($hv, 2)
    if ($r["tv"]) { $script:mount.tv = [int]$r["tv"] }   # the game's Kinect framing the player's feet to raised hands (calib::VirtualTilt)
    $script:mount.cal = (Get-Date).ToString("yyyy-MM-dd")
    Pick "sensorload" $r["sensorload"]
    Save
    return $true
}

# The camera placement, by hand (advanced): what Calibrate camera... fills by itself, to fine-tune or to type.
function PlacementDialog($owner) {
    $d = New-Object Windows.Forms.Form -Property @{ Text = "Camera placement (advanced)"; StartPosition = "CenterParent"; FormBorderStyle = "FixedDialog"
                                                   MaximizeBox = $false; MinimizeBox = $false; Font = $owner.Font; AutoScaleMode = "Font"
                                                   ClientSize = New-Object Drawing.Size(470, 360) }
    $t = New-Object Windows.Forms.TableLayoutPanel -Property @{ Dock = "Fill"; ColumnCount = 2; Padding = New-Object Windows.Forms.Padding(12) }
    $on = New-Object Windows.Forms.CheckBox -Property @{ Text = "Place the camera for the game (recommended: its hand cursor needs it)"; AutoSize = $true; Checked = [bool]$mount.on }
    $t.Controls.Add($on); $t.SetColumnSpan($on, 2)
    $fields = [ordered]@{ hr = @("Camera height from the floor (m)", 0.2, 3.0, 2); tr = @("Camera tilt (degrees, looking down is negative)", -45, 45, 1)
                          hfov = @("Camera lens: horizontal view (degrees)", 40, 120, 0); hv = @("Hand cursor height (m; lower raises the cursor)", 0.5, 3.0, 2)
                          tv = @("Hand cursor tilt (degrees)", -27, 27, 0) }
    $boxes = @{}
    $labels = @()
    foreach ($k in $fields.Keys) {
        $f = $fields[$k]
        $l = New-Object Windows.Forms.Label -Property @{ Text = $f[0]; AutoSize = $true; Anchor = "Left" }
        $n = New-Object Windows.Forms.NumericUpDown -Property @{ Minimum = $f[1]; Maximum = $f[2]; DecimalPlaces = $f[3]; Width = 80
                                                                 Increment = $(if ($f[3] -eq 2) { 0.05 } elseif ($f[3] -eq 1) { 0.5 } else { 1 }) }
        $n.Value = [Math]::Min($n.Maximum, [Math]::Max($n.Minimum, [decimal]$mount[$k]))   # after the limits: a hashtable sets them in any order
        $t.Controls.Add($l); $t.Controls.Add($n); $boxes[$k] = $n; $labels += $l
    }
    $lock = { foreach ($c in @($boxes.Values) + $labels) { $c.Enabled = $on.Checked } }   # unticked: greyed, so it shows off
    $on.Add_CheckedChanged($lock)
    & $lock
    $note = New-Object Windows.Forms.Label -Property @{ AutoSize = $true; MaximumSize = New-Object Drawing.Size(440, 0)
        Text = "Calibrate camera... in the main window fills these by itself. Change them here only to fine-tune. Unticked, the game gets the camera as it is, as if it were its Kinect. The lens is in the camera's specifications (most webcams: 65-80)." }
    $t.Controls.Add($note); $t.SetColumnSpan($note, 2)
    $ok = New-Object Windows.Forms.Button -Property @{ Text = "OK"; DialogResult = "OK"; Width = 90 }
    $t.Controls.Add($ok)
    $d.AcceptButton = $ok
    $d.Controls.Add($t)
    if ($d.ShowDialog($owner) -eq "OK") {
        $typed = $script:mount.on -ne $on.Checked
        $script:mount.on = $on.Checked
        foreach ($k in $boxes.Keys) { if ([double]$boxes[$k].Value -ne [double]$script:mount[$k]) { $typed = $true }; $script:mount[$k] = [double]$boxes[$k].Value }
        if ($typed) { $script:mount.cal = "" }
        Save
    }
}

# The game makes its window ~40 s after Play, when Windows no longer lets a background process take the
# foreground: a full-screen window left behind minimises, and it looks as if nothing started. For the boot's
# first two minutes, whenever a window of the game is shown but another program is in front, bring the game forward.
function ForegroundGame($game) {
    Add-Type -Namespace Kdm -Name Win -MemberDefinition @'
[DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
[DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
[DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
[DllImport("user32.dll")] public static extern void SwitchToThisWindow(IntPtr h, bool altTab);
'@
    $until = (Get-Date).AddSeconds(120)
    while (-not $game.HasExited -and (Get-Date) -lt $until) {
        $game.Refresh()
        $h = $game.MainWindowHandle
        [uint32]$front = 0
        [void][Kdm.Win]::GetWindowThreadProcessId([Kdm.Win]::GetForegroundWindow(), [ref]$front)
        if ($h -ne [IntPtr]::Zero -and [Kdm.Win]::IsWindowVisible($h)) {
            if ($front -eq $game.Id) { return }   # in front once: from here on, leaving it is the player's choice
            [Kdm.Win]::SwitchToThisWindow($h, $true)
        }
        Start-Sleep -Milliseconds 500
    }
}

# The cameras Windows sees, by name (kdmsensor.exe --list), without a console window.
function Cameras {
    if (-not (Test-Path -LiteralPath $sensorExe)) { return @() }
    $psi = New-Object Diagnostics.ProcessStartInfo -Property @{ FileName = $sensorExe; Arguments = "--list"; UseShellExecute = $false
                                                               RedirectStandardOutput = $true; CreateNoWindow = $true
                                                               StandardOutputEncoding = [Text.Encoding]::UTF8 }
    $p = [Diagnostics.Process]::Start($psi)
    $out = $p.StandardOutput.ReadToEnd()
    $p.WaitForExit()
    @($out -split "`r?`n" | Where-Object { $_ })
}

# Sets one value, then what it needs (recursively), then resets whatever lost a need.
function Pick($oid, $vid) {
    $script:sel[$oid] = $vid
    $todo = New-Object System.Collections.Generic.Queue[string]
    foreach ($n in (Needs (Val $oid $vid))) { $todo.Enqueue($n) }
    while ($todo.Count) {
        $o, $v = $todo.Dequeue() -split "\."
        if ($script:sel[$o] -ne $v) {
            $script:sel[$o] = $v
            Write-Host ("  -> {0} switched to '{1}' (needed by {2})" -f (Opt $o).title, (Val $o $v).label, (Opt $oid).title)
            foreach ($n in (Needs (Val $o $v))) { $todo.Enqueue($n) }
        }
    }
    do {
        $changed = $false
        foreach ($o in $cat.options) {
            foreach ($n in (Needs (Val $o.id $script:sel[$o.id]))) {
                $no, $nv = $n -split "\."
                if ($script:sel[$no] -ne $nv) {
                    Write-Host ("  -> {0} back to '{1}': it needs {2} = '{3}'" -f $o.title, $o.values[0].label, (Opt $no).title, (Val $no $nv).label)
                    $script:sel[$o.id] = $o.values[0].id
                    $changed = $true
                }
            }
        }
    } while ($changed)
}

# ONLINE the game is the server's and Konami's (the user, 2026-11-21): with a server set, the options that change the score
# ("lock_online" in the catalogue: Game rules, Stealth) are Konami's value, whatever was chosen; the choice stays saved for offline.
# The server is spice2x's url option (spice2x settings... > Options, in mods\conf\spicetools.xml); empty, or spice2x's own local
# e-amusement (port 8080), is no server. shortcut: an unreadable file counts as no server, not a refusal to open.
function ServerUrl {
    try {
        $x = [xml](Get-Content -LiteralPath (Join-Path $mods "conf\spicetools.xml") -Raw)
        $u = ([string]$x.SelectSingleNode("//game[@name='Dance Evolution']/options/option[@name='url']/@value").Value).Trim()
    } catch { return "" }
    if ($u -match '^https?://(localhost|127\.0\.0\.1):8080/?$') { "" } else { $u }
}
function OnlineLocked { if (ServerUrl) { @($cat.options | Where-Object { $_.PSObject.Properties["lock_online"] }) } else { @() } }
# the selection as the game gets it: the choice, with the locked options at Konami's value
function Eff { $e = $script:sel.Clone(); foreach ($o in (OnlineLocked)) { $e[$o.id] = $o.values[0].id }; $e }

function Save { ($script:sel + @{ camera = $script:camera; mount = $script:mount }) | ConvertTo-Json | Set-Content -LiteralPath $selPath -Encoding UTF8 }

# The window: one list per option, grouped by sector; the text box explains the option in focus.
# Returns $true when the player pressed Play and mods\active is built.
function Menu {
    [Windows.Forms.Application]::EnableVisualStyles()
    $form = New-Object Windows.Forms.Form -Property @{
        Text = "DanceEvolution ARCADE"; StartPosition = "CenterScreen"; FormBorderStyle = "FixedDialog"; MaximizeBox = $false
        Font = New-Object Drawing.Font("Segoe UI", 9); AutoScaleMode = "Font"
        ClientSize = New-Object Drawing.Size(560, [Math]::Min(790, [Windows.Forms.Screen]::PrimaryScreen.WorkingArea.Height - 60)) }
    $grid = New-Object Windows.Forms.TableLayoutPanel -Property @{ Dock = "Fill"; AutoScroll = $true; ColumnCount = 2; Padding = New-Object Windows.Forms.Padding(14, 6, 14, 6) }
    [void]$grid.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle("Percent", 42)))
    [void]$grid.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle("Percent", 58)))
    $help = New-Object Windows.Forms.TextBox -Property @{ Dock = "Bottom"; Multiline = $true; ReadOnly = $true; Height = 96; ScrollBars = "Vertical" }
    $bar = New-Object Windows.Forms.FlowLayoutPanel -Property @{ Dock = "Bottom"; Height = 46; FlowDirection = "RightToLeft"; Padding = New-Object Windows.Forms.Padding(10, 8, 10, 0) }
    $play = New-Object Windows.Forms.Button -Property @{ Text = "Play"; Width = 110; Height = 30 }
    $keys = New-Object Windows.Forms.Button -Property @{ Text = "spice2x settings..."; Width = 140; Height = 30 }
    $look = New-Object Windows.Forms.Button -Property @{ Text = "Sensor preview..."; Width = 130; Height = 30 }
    $upd = New-Object Windows.Forms.Button -Property @{ Text = "Check for updates"; Width = 130; Height = 30; Enabled = $false }
    $state = New-Object Windows.Forms.Label -Property @{ AutoSize = $true; Margin = New-Object Windows.Forms.Padding(0, 7, 8, 0) }
    $bar.Controls.AddRange(@($play, $keys, $look))
    if (Get-KdmInstalled $mods) { $bar.Controls.Add($upd) }   # a release install only: the project's own folder has nothing to update
    $bar.Controls.Add($state)
    $intro = "Choose your mods: every change is saved. Each option's first value is Konami's original.`r`n`r`n" +
             "Before your first game: spice2x settings..., to bind your buttons (the cabinet has no keyboard: there are no default buttons)."
    $help.Text = $intro

    $combos = @{}
    $optLabels = @{}
    $sector = $null
    $srv = New-Object Windows.Forms.Label -Property @{ AutoSize = $true; MaximumSize = New-Object Drawing.Size(500, 0); ForeColor = "Firebrick"; Visible = $false }   # the online lock's line
    $grid.Controls.Add($srv)
    $grid.SetColumnSpan($srv, 2)
    foreach ($o in $menu) {
        if ($o.sector -ne $sector) {
            $sector = $o.sector
            $h = New-Object Windows.Forms.Label -Property @{ Text = $sector.ToUpperInvariant(); AutoSize = $true; Margin = New-Object Windows.Forms.Padding(0, 12, 0, 2)
                                                          Font = New-Object Drawing.Font("Segoe UI", 9, [Drawing.FontStyle]::Bold) }
            $grid.Controls.Add($h)
            $grid.SetColumnSpan($h, 2)
        }
        $l = New-Object Windows.Forms.Label -Property @{ Text = $o.title; AutoSize = $true; Anchor = "Left" }
        $optLabels[$o.id] = $l
        $c = New-Object Windows.Forms.ComboBox -Property @{ DropDownStyle = "DropDownList"; Dock = "Fill"; Tag = $o }
        foreach ($v in (Shown $o)) { [void]$c.Items.Add($v.label) }
        $grid.Controls.Add($l)
        $grid.Controls.Add($c)
        $combos[$o.id] = $c
        if ($o.id -eq "sensor") {   # the webcam's camera, right under the sensor
            $cl = New-Object Windows.Forms.Label -Property @{ Text = "Camera"; AutoSize = $true; Anchor = "Left" }
            $script:camCombo = New-Object Windows.Forms.ComboBox -Property @{ DropDownStyle = "DropDownList"; Dock = "Fill" }
            $grid.Controls.Add($cl)
            $grid.Controls.Add($camCombo)
            $script:camLabel = $cl
            $script:calBtn = New-Object Windows.Forms.Button -Property @{ Text = "Calibrate camera..."; AutoSize = $true; Font = New-Object Drawing.Font("Segoe UI", 9, [Drawing.FontStyle]::Bold) }
            $script:placeBtn = New-Object Windows.Forms.Button -Property @{ Text = "Advanced..."; AutoSize = $true }
            $script:calRow = New-Object Windows.Forms.FlowLayoutPanel -Property @{ AutoSize = $true; WrapContents = $false; Margin = New-Object Windows.Forms.Padding(0) }
            $calRow.Controls.AddRange(@($calBtn, $placeBtn))
            $script:calState = New-Object Windows.Forms.Label -Property @{ AutoSize = $true; MaximumSize = New-Object Drawing.Size(300, 0); Anchor = "Left" }
            $grid.Controls.Add($calState)
            $grid.Controls.Add($calRow)
        }
    }
    $filler = New-Object Windows.Forms.Label -Property @{ AutoSize = $true }   # the last row takes the spare height, not an option's
    $grid.Controls.Add($filler)
    $grid.SetColumnSpan($filler, 2)
    $describe = {
        param($o)
        $v = Val $o.id $sel[$o.id]
        $t = "{0}: {1}" -f $o.title, $o.help
        if ($v.PSObject.Properties["help"]) { $t += "`r`n`r`n{0}: {1}" -f $v.label, $v.help }
        $nd = Needs $v
        if ($nd.Count) { $t += "`r`nSwitches on: " + (($nd | ForEach-Object { $a, $b = $_ -split "\."; "{0} = {1}" -f (Opt $a).title, (Val $a $b).label }) -join ", ") }
        $help.Text = $t
    }
    # A preview or the controls run beside this window: the options stay as they are, only the buttons wait, so nothing is left
    # painted grey by a window that cannot repaint (form.Enabled = false while blocked on the child), and the preview can still be closed from here.
    $script:child = $null
    $script:filesOk = $false
    $childTimer = New-Object Windows.Forms.Timer -Property @{ Interval = 300 }
    $runChild = {
        param($p)
        $script:child = $p
        $play.Enabled = $keys.Enabled = $look.Enabled = $upd.Enabled = $false
        $childTimer.Start()
    }
    $childTimer.Add_Tick({
        if ($script:child -and -not $script:child.HasExited) { return }
        $childTimer.Stop()
        $script:child = $null
        $keys.Enabled = $look.Enabled = $true
        $play.Enabled = $upd.Enabled = $script:filesOk
        & $sync   # spice2x settings... may have set or cleared the server
    })
    $form.Add_FormClosing({ if ($script:child -and -not $script:child.HasExited -and $script:child.ProcessName -eq "kdmsensor") { $script:child.Kill() } })
    $script:busy = $false
    $sync = {   # every list shows the selection, after Pick switched needs on or off
        $script:busy = $true
        foreach ($o in $menu) { $combos[$o.id].SelectedIndex = [Math]::Max(0, [array]::IndexOf([string[]]@((Shown $o) | ForEach-Object { $_.id }), [string]$sel[$o.id])) }
        $lk = @(OnlineLocked)   # a server is set: the options that change the score show Konami's value, greyed (the saved choice stays)
        foreach ($o in $menu) { $combos[$o.id].Enabled = -not ($lk | Where-Object { $_.id -eq $o.id }); if (-not $combos[$o.id].Enabled) { $combos[$o.id].SelectedIndex = 0 } }
        $srv.Visible = [bool]$lk.Count
        if ($lk.Count) { $srv.Text = "Playing on a server: {0} stay Konami's, they would change the score. To use them, clear the server's URL in spice2x settings... (Options), then they work offline." -f (($lk | ForEach-Object { $_.title }) -join ", ") }
        $web = $sel["sensor"] -eq "webcam"   # the webcam's rows only with the webcam
        if ($camCombo) { foreach ($c in @($camLabel, $camCombo, $calState, $calRow)) { $c.Visible = $web }; $camCombo.Enabled = $camCombo.Items.Count -gt 0 }
        if ($combos["sensorload"]) { $combos["sensorload"].Visible = $optLabels["sensorload"].Visible = $web }
        $script:busy = $false
    }
    if ($camCombo) {
        $cams = @(Cameras)   # @(): one camera would come back as a bare string, and $cams[0] its first letter
        foreach ($n in $cams) { [void]$camCombo.Items.Add($n) }
        if (-not $cams.Count) { [void]$camCombo.Items.Add("(no camera connected)") }
        $camCombo.SelectedIndex = [Math]::Max(0, [array]::IndexOf([string[]]$cams, $camera))
        if ($cams.Count) { $script:camera = $cams[$camCombo.SelectedIndex] }
        $camCombo.Add_SelectedIndexChanged({
            if ($script:busy -or -not $cams.Count) { return }
            $script:camera = $cams[$this.SelectedIndex]
            Save
            if ($calText) { & $calText }   # the filter-camera warning follows the camera
        })
        $camCombo.Add_Enter({ $help.Text = "Camera: the one the webcam sensor uses, when Body sensor is a webcam. Sensor preview... shows it as the game will see it." })
    }
    if ($placeBtn) {
        $calText = {
            $inv = [Globalization.CultureInfo]::InvariantCulture
            $where = "camera {0} m, tilt {1} degrees" -f ([double]$mount.hr).ToString("0.00", $inv), ([double]$mount.tr).ToString("+0.0;-0.0", $inv)
            if (-not $mount.on) { $calState.Text = "Not calibrated: the camera as it is"; $calState.ForeColor = "Firebrick" }
            elseif ($mount.cal) { $calState.Text = "Calibrated {0}: {1}" -f $mount.cal, $where; $calState.ForeColor = "ForestGreen" }
            else { $calState.Text = "Typed by hand: {0}" -f $where; $calState.ForeColor = "DarkGoldenrod" }
            # cameras known for filters and effects (WEBCAM_SENSOR.md 3h): warned, never refused; phone cameras are virtual too and pass
            if ($script:camera -match "OBS Virtual Camera|NVIDIA Broadcast|XSplit VCam|Snap Camera") {
                $calState.Text += "`r`nWarning: {0} can add filters or effects to the picture; turn them all off for play." -f $Matches[0]
                $calState.ForeColor = "Firebrick"
            }
        }
        & $calText
        $calBtn.Add_Click({
            $play.Enabled = $keys.Enabled = $look.Enabled = $upd.Enabled = $calBtn.Enabled = $placeBtn.Enabled = $false   # only Play holds the window: the rest just waits
            try { [void](Calibrate) } finally { $keys.Enabled = $look.Enabled = $calBtn.Enabled = $placeBtn.Enabled = $true; $play.Enabled = $upd.Enabled = $script:filesOk }
            & $calText; & $sync
        })
        $calBtn.Add_Enter({ $help.Text = "Calibrate camera: once where you play, about a minute in front of the camera, nothing typed. It finds the camera's height and tilt, sets the hand cursor for your arm at shoulder height (the song selector) and checks you reach OK, checks the game keeps you when you crouch, and chooses CPU or GPU. Calibrate again if you move the camera or the room changes." })
        $placeBtn.Add_Click({ PlacementDialog $form; & $calText; & $sync })
        $placeBtn.Add_Enter({ $help.Text = "Advanced: the camera's height, tilt and lens and the hand cursor's height, by hand. Calibrate camera... fills them by itself." })
    }
    $look.Add_Click({   # the chosen sensor, live: the picture, the depth and players, the skeleton the game gets
        if (-not (Test-Path -LiteralPath $sensorExe)) { [void][Windows.Forms.MessageBox]::Show("mods\webcam is missing.", "Sensor preview"); return }
        $a = if ($sel["sensor"] -eq "webcam") { "--preview " + (SensorArgs) } else { "--preview --kinect" }
        $psi = New-Object Diagnostics.ProcessStartInfo -Property @{ FileName = $sensorExe; Arguments = $a; UseShellExecute = $false; CreateNoWindow = $true }
        & $runChild ([Diagnostics.Process]::Start($psi))
    })
    $look.Add_Enter({ $help.Text = "Sensor preview: the chosen sensor live (the Kinect, or the chosen camera through the webcam sensor), with the skeleton and the player the game will get. Close it before Play." })
    foreach ($c in $combos.Values) {
        $c.Add_SelectedIndexChanged({
            if ($script:busy) { return }
            $o = $this.Tag
            Pick $o.id (Shown $o)[$this.SelectedIndex].id
            & $sync
            Save
            & $describe $o
        })
        $c.Add_Enter({ & $describe $this.Tag })
    }
    $keys.Add_Click({
        & $runChild (Start-Process (Join-Path $mods "bin\spice.exe") -ArgumentList ('-cfg -cfgpath "{0}"' -f (Join-Path $mods "conf\spicetools.xml")) -WorkingDirectory ([WildcardPattern]::Escape($root)) -PassThru)   # Start-Process has no literal form
    })
    $script:go = $false
    $play.Add_Click({
        $form.Enabled = $false
        $form.UseWaitCursor = $true
        $help.Text = "Preparing the game..."
        [Windows.Forms.Application]::DoEvents()
        try {
            Save
            [void](Build)
            $script:go = $true
            $form.Close()
        } catch {
            [void][Windows.Forms.MessageBox]::Show("$_", "Could not prepare the game")
            $form.Enabled = $true
            $form.UseWaitCursor = $false
            $help.Text = $intro
        }
    })
    $form.AcceptButton = $play
    # The look for a newer release, at opening ($manual false: says nothing when there is nothing new) and from the button ($manual: says the outcome).
    $checkUpdate = {
        param($manual)
        $inst = Get-KdmInstalled $mods
        if (-not $inst) { return }
        $say = { param($t) $state.ForeColor = "Black"; $state.Text = $t; [Windows.Forms.Application]::DoEvents() }
        $play.Enabled = $upd.Enabled = $false
        & $say "Looking for updates..."
        $r = Find-KdmUpdate $inst $null ([IO.Path]::GetTempPath())
        if ($form.IsDisposed) { return }
        $ready = { $state.ForeColor = "ForestGreen"; $state.Text = "Game files OK: ready to play"; $play.Enabled = $upd.Enabled = -not $script:child }
        if ($r.status -eq "newer" -and (Show-KdmUpdate $inst $r.rel)) {
            $form.Enabled = $false
            try {
                Install-KdmUpdate $root $r.rel $say
                [void][Windows.Forms.MessageBox]::Show("Updated to version $($r.rel.version). The launcher opens again.", "DanceEvolution ARCADE")
                Start-Process "$PSHOME\powershell.exe" -ArgumentList ('-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}" -Elevated' -f $PSCommandPath)
                $script:reopening = $true; $form.Close(); return
            } catch {
                [void][Windows.Forms.MessageBox]::Show("The update failed: $_`r`n`r`nYou keep version $($inst.version): nothing was replaced.", "DanceEvolution ARCADE")
            }
            $form.Enabled = $true
        }
        & $ready
        if ($manual) { $state.Text = $r.text; if ($r.status -in "offline", "none") { $state.ForeColor = "DarkGoldenrod" } }
    }
    $upd.Add_Click({ & $checkUpdate $true })
    $upd.Add_Enter({ $help.Text = "Check for updates: looks now at the project's latest release, the same look the launcher makes each time it opens. If a newer version is there it shows what changed, with Update and Not now." })
    $form.Add_Shown({
        [void]$play.Focus(); $help.Text = $intro   # the intro (bind your controls) first, not the first option's help
        $play.Enabled = $false; $state.Text = "Checking the game's files..."; [Windows.Forms.Application]::DoEvents()
        $bad = Altered   # the safety check, here instead of a message: Play only when Konami's files are whole
        if ($form.IsDisposed) { return }   # closed while it checked (the window answers during the check)
        $need = MissingRuntime
        if ($bad) { $state.ForeColor = "Firebrick"; $state.Text = "Not Konami's originals: " + ($bad -join ", ") }
        elseif ($need) {
            $state.ForeColor = "Firebrick"; $state.Text = "Missing: DirectX runtime (June 2010)"
            $help.Text = "The game cannot start on this PC yet: Windows does not have $need.`r`n`r`nInstall Microsoft's `"DirectX End-User Runtimes (June 2010)`", then open the launcher again."
            return
        }
        else { $script:filesOk = $true; $state.ForeColor = "ForestGreen"; $state.Text = "Game files OK: ready to play"; $play.Enabled = -not $script:child; [void]$play.Focus() }
        # A release install (mods\generator, mods\version.json; the project's own folder has neither): first the content a Konami base cannot
        # give and the mods made from the player's own files, then a look at the newest release (update.ps1).
        if ($script:filesOk -and (Test-Path -LiteralPath (Join-Path $mods "generator"))) {
            $play.Enabled = $false
            $say = { param($t) $state.ForeColor = "Black"; $state.Text = $t; [Windows.Forms.Application]::DoEvents() }
            $problem = Initialize-KdmContent $root $say
            if ($form.IsDisposed) { return }
            if ($problem) { $script:filesOk = $false; $state.ForeColor = "Firebrick"; $state.Text = "Setup needed: see below"; $help.Text = $problem; return }
            $state.ForeColor = "ForestGreen"; $state.Text = "Game files OK: ready to play"; $play.Enabled = -not $script:child
        }
        if ($script:filesOk) { & $checkUpdate $false; if ($form.IsDisposed -or $script:reopening) { return } }
        $cfg = Join-Path $mods "conf\spicetools.xml"   # spice2x writes vkey 255 for a button nobody bound
        if (-not ((Test-Path -LiteralPath $cfg) -and (Select-String -LiteralPath $cfg -Pattern 'vkey="(?!255")\d+"' -Quiet))) {
            $state.ForeColor = "DarkGoldenrod"; $state.Text = "First: spice2x settings..., to bind your buttons"; [void]$keys.Focus()
        }
    })
    $form.Controls.AddRange(@($grid, $help, $bar))   # docked from the last: the buttons at the very bottom
    foreach ($o in $menu) { if (@((Shown $o) | ForEach-Object { $_.id }) -notcontains $sel[$o.id]) { Pick $o.id (Shown $o)[0].id } }   # a saved value this screen cannot show
    & $sync
    [void]$form.ShowDialog()
    return $script:go
}

# The Diagnostic log's report: one zip to send back. summary.txt says what this PC is and, mod by mod, what is really in the built
# copy (each code edit's bytes, each data folder); beside it the logs of this game: spice2x and the game, our proxy, the webcam sensor.
function Report($chosen, $code, $started) {
    $sel = Eff
    $dir = Join-Path $mods "reports"
    New-Item -ItemType Directory -Force $dir | Out-Null
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $zipPath = Join-Path $dir "report-$stamp.zip"
    # the two private names, whole words only: a user called "a" must not eat the log
    $private = @($env:COMPUTERNAME, $env:USERNAME) | Where-Object { $_ }
    $clean = { param($t) foreach ($w in $private) { $t = $t -ireplace ("(?<![A-Za-z0-9])" + [regex]::Escape($w) + "(?![A-Za-z0-9])"), "[removed]" }; $t }
    $s = New-Object Text.StringBuilder
    $add = { param($t) [void]$s.AppendLine((& $clean $t)) }
    & $add ("DanceEvolution report {0}, game exit code {1}, played {2:HH:mm:ss} to {3:HH:mm:ss}" -f $stamp, $code, $started, (Get-Date))
    $os = Get-CimInstance Win32_OperatingSystem
    & $add ("Windows: {0} build {1}, RAM {2:N1} GB" -f $os.Caption, $os.BuildNumber, ($os.TotalVisibleMemorySize / 1MB))
    Get-CimInstance Win32_Processor | ForEach-Object { & $add ("CPU: {0}, {1} cores, {2} threads" -f $_.Name.Trim(), $_.NumberOfCores, $_.NumberOfLogicalProcessors) }
    Get-CimInstance Win32_VideoController | ForEach-Object { & $add ("GPU: {0}, driver {1}, now {2}x{3} at {4} Hz" -f $_.Name, $_.DriverVersion, $_.CurrentHorizontalResolution, $_.CurrentVerticalResolution, $_.CurrentRefreshRate) }
    & $add ("Main screen's modes: " + ((ScreenModes) -join " "))
    if ($sel["sensor"] -eq "webcam") { & $add ("Camera: {0}; placement {1}" -f $camera, (($mount.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join " ")) }
    & $add ""
    & $add "Option: value: what the built copy holds"
    $files = @{}
    foreach ($o in $cat.options) {
        $v = Val $o.id $sel[$o.id]
        $notes = @()
        if ($v.PSObject.Properties["patches"] -and $v.patches) {
            $good = 0
            foreach ($p in $v.patches) {
                if (-not $files[$p.dllName]) { $files[$p.dllName] = [IO.File]::ReadAllBytes((Join-Path $active ("modules\" + $p.dllName))) }
                $want = $p.dataEnabled
                $at = [int]$p.offset
                $have = -join ($files[$p.dllName][$at..($at + $want.Length / 2 - 1)] | ForEach-Object { $_.ToString("x2") })
                if ($have -eq $want.ToLower()) { $good++ }
            }
            $notes += "code edits in place {0}/{1}" -f $good, @($v.patches).Count
        }
        if ($v.PSObject.Properties["data"]) { foreach ($d in @($v.data)) { $notes += "data {0}: {1}" -f $d, $(if (Test-Path -LiteralPath (Join-Path $mods "data\$d")) { "present" } else { "MISSING" }) } }
        if ($v.PSObject.Properties["env"]) { $notes += "set " + (($v.env.PSObject.Properties | ForEach-Object { $_.Name }) -join ", ") }
        if ($v.PSObject.Properties["laa"]) { $b = [IO.File]::ReadAllBytes((Join-Path $active "spice.exe")); $notes += "4 GB bit " + $(if ([BitConverter]::ToUInt16($b, [BitConverter]::ToInt32($b, 0x3C) + 22) -band 0x20) { "set" } else { "NOT SET" }) }
        if ($v.PSObject.Properties["sensor"]) { $notes += "arguments " + (SensorArgs) }
        if ($o.id -eq "workers" -and $v.id -eq "auto") { $notes += "pool of {0} threads" -f [Math]::Max(1, [Math]::Min(4, [Environment]::ProcessorCount - 2)) }
        & $add ("{0}: {1}: {2}" -f $o.title, $v.label, $(if ($notes) { $notes -join "; " } else { "nothing changed" }))
    }
    Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
    $zip = [IO.Compression.ZipFile]::Open($zipPath, "Create")
    try {
        $put = {
            param($name, $text)
            $w = New-Object IO.StreamWriter($zip.CreateEntry($name).Open())
            try { $w.Write($text) } finally { $w.Dispose() }
        }
        & $put "summary.txt" $s.ToString()
        # only what this game wrote: an older log would describe another session
        $logs = @{ "log.txt" = Join-Path $mods "conf\log.txt"; "kdmsensor.log" = Join-Path $mods "webcam\kdmsensor.log"; "kinect10.log" = Join-Path $active "kinect10.log"; "d3d9diag.log" = Join-Path $active "d3d9diag.log" }
        foreach ($k in $logs.Keys) {
            $f = Get-Item -LiteralPath $logs[$k] -ErrorAction SilentlyContinue
            if ($f -and $f.LastWriteTime -ge $started) { & $put $k (& $clean ([IO.File]::ReadAllText($f.FullName))) }
        }
        Get-ChildItem -LiteralPath $root -Filter "*.dmp" | Where-Object { $_.LastWriteTime -ge $started } | ForEach-Object { [void][IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $_.FullName, $_.Name) }
    } finally { $zip.Dispose() }
    $zipPath
}

# Hard links need NTFS: on an exFAT or FAT32 drive the sound files are copied instead (mods\snd is rebuilt, the originals are not touched).
function SoundFile($dst, $src) {
    try { New-Item -ItemType HardLink -Path $dst -Target $src -ErrorAction Stop | Out-Null } catch { Copy-Item -LiteralPath $src -Destination $dst -Force }
}

# .NET, not Get-FileHash: that cmdlet needs a module a broken PSModulePath hides. In pieces, the window's messages served
# between them: the files check reads 1 GB, tens of seconds on a USB disk, and a window that does not answer looks hung.
function Md5($path) {
    $h = [Security.Cryptography.MD5]::Create()
    $s = [IO.File]::OpenRead($path)
    $buf = New-Object byte[] (4MB)
    try {
        while (($n = $s.Read($buf, 0, $buf.Length)) -gt 0) { [void]$h.TransformBlock($buf, 0, $n, $null, 0); [Windows.Forms.Application]::DoEvents() }
        [void]$h.TransformFinalBlock($buf, 0, 0)
        ([BitConverter]::ToString($h.Hash) -replace "-", "").ToLower()
    } finally { $s.Dispose() }
}

# What the game needs and Windows does not bring: gamekdm.dll imports d3dx9_43.dll, part of the DirectX runtime of June 2010.
# Without it the game ends at once with an error code and no word of why.
function MissingRuntime {
    $places = @([Environment]::GetFolderPath("SystemX86"), $root, (Join-Path $root "modules"))
    if (-not ($places | Where-Object { Test-Path -LiteralPath (Join-Path $_ "d3dx9_43.dll") })) { "the DirectX runtime of June 2010 (d3dx9_43.dll)" }
}

# Every game file a session could reach (modules\, data\sound\, each data\ file a mod overlays), against
# Konami's MD5 in the catalogue: returns the ones that differ or are missing. About 5 s.
function Altered {
    @($cat.originals.PSObject.Properties | Where-Object {
        $f = Join-Path $root $_.Name
        -not (Test-Path -LiteralPath $f) -or (Md5 $f) -ne $_.Value } | ForEach-Object { $_.Name })
}

# The game's saved settings (T149, the user's decision 2026-11-23): Game mode writes what the SERVICE MENU writes, so the game and a
# server only ever see a state an operator can make. Free play is `coin.xml <freeplay>` and `testmode-v.xml <freeplay><current>`
# (and the menu's save marks `<e_amusement><fixed>`), each file a text RC4-encrypted per 768-byte block with a key of 32 zeros, the four
# mirrors in nvram\0..3, info.bin the directory (the MD5 of each stored file, and its own MD5 last), testmode-v.crc the crc32 of the text.
# Read from libavs's avs-nvram.c; the same code in Python, with the proof against the user's menu-made files: _tools\mods\game_rules\nvram.py.
function NvRc4([int]$n) {
    $s = New-Object byte[] 256
    for ($i = 0; $i -lt 256; $i++) { $s[$i] = $i }
    $j = 0
    for ($i = 0; $i -lt 256; $i++) { $j = ($j + $s[$i]) -band 255; $t = $s[$i]; $s[$i] = $s[$j]; $s[$j] = $t }
    $o = New-Object byte[] $n; $i = 0; $j = 0
    for ($k = 0; $k -lt $n; $k++) {
        $i = ($i + 1) -band 255; $j = ($j + $s[$i]) -band 255; $t = $s[$i]; $s[$i] = $s[$j]; $s[$j] = $t
        $o[$k] = $s[($s[$i] + $s[$j]) -band 255]
    }
    , $o
}
function NvXor([byte[]]$d, [byte[]]$ks) {   # the keystream repeats every ks.Length bytes (a block; info.bin's one stream is as long as the file)
    $o = New-Object byte[] $d.Length
    for ($i = 0; $i -lt $d.Length; $i++) { $o[$i] = $d[$i] -bxor $ks[$i % $ks.Length] }
    , $o
}
function NvMd5([byte[]]$d) { , [Security.Cryptography.MD5]::Create().ComputeHash($d) }
function NvCrc32([byte[]]$d, [int]$n) {
    $t = New-Object 'uint32[]' 256
    for ($i = 0; $i -lt 256; $i++) {
        $c = [uint32]$i
        for ($k = 0; $k -lt 8; $k++) { if ($c -band 1) { $c = [uint32](3988292384 -bxor ($c -shr 1)) } else { $c = [uint32]($c -shr 1) } }
        $t[$i] = $c
    }
    $c = [uint32]4294967295
    for ($i = 0; $i -lt $n; $i++) { $c = [uint32]($t[($c -bxor $d[$i]) -band 255] -bxor ($c -shr 8)) }
    [uint32]($c -bxor 4294967295)
}
function NvRecord([byte[]]$info, [string]$name) {
    for ($n = 0; $n -lt 128; $n++) {
        $o = 0x28 + $n * 0xb8
        if ([Text.Encoding]::ASCII.GetString($info, $o + 0xa8, 16).Split([char]0)[0] -eq $name) { return $o }
    }
    throw "$name is not in info.bin"
}
# a file's text as a latin-1 string (every byte one char: Shift-JIS survives the round trip) and the zeros after it
function NvLoad($root, [byte[]]$info, $name, [byte[]]$ks) {
    $enc = [IO.File]::ReadAllBytes((Join-Path $root "0\$name"))
    foreach ($m in 1..3) { if (-not [Linq.Enumerable]::SequenceEqual($enc, [IO.File]::ReadAllBytes((Join-Path $root "$m\$name")))) { throw "$name : the mirrors differ" } }
    $o = NvRecord $info $name
    if (-not [Linq.Enumerable]::SequenceEqual((NvMd5 $enc), [byte[]]($info[($o + 0x98)..($o + 0xa7)]))) { throw "$name does not match info.bin" }
    $plain = NvXor $enc $ks
    $size = [int][BitConverter]::ToUInt64($info, $o + 0x90)
    $tail = if ($size -lt $plain.Length) { [byte[]]$plain[$size..($plain.Length - 1)] } else { [byte[]]@() }
    @{ text = [Text.Encoding]::GetEncoding(28591).GetString($plain, 0, $size); tail = $tail }
}
function NvSet($f, [string]$pattern, [string]$v) {
    $rx = New-Object Text.RegularExpressions.Regex($pattern, "Singleline")
    if (-not $rx.IsMatch($f.text)) { throw "a setting is not where the menu keeps it" }
    $f.text = $rx.Replace($f.text, ('${1}' + $v + '${3}'), 1)
}
# Free play on or off, as the menu writes it; returns the files changed ('' when the settings already were so). Throws, writing nothing, when
# the settings are not what this knows (another layout, half written, mirrors apart): the game is then started as it is.
function NvSetFreePlay($root, [bool]$on) {
    $nv = Join-Path $root "info.bin.new"
    if ((Test-Path -LiteralPath $nv) -and (Get-Item -LiteralPath $nv).Length) { throw "a write is pending (info.bin.new): start the game once first" }
    $info = NvXor ([IO.File]::ReadAllBytes((Join-Path $root "info.bin"))) (NvRc4 23636)
    $head = [BitConverter]::ToUInt32($info, 4), [BitConverter]::ToUInt32($info, 8), [BitConverter]::ToUInt32($info, 12)
    if ($info.Length -ne 23636 -or $info[0] -ne 0x5a -or $info[1] -ne 0xc0 -or $info[2] -ne 0x38 -or $info[3] -ne 0xda -or ($head -join ",") -ne "768,4,128") { throw "info.bin is not the layout this knows" }
    if (-not [Linq.Enumerable]::SequenceEqual((NvMd5 ([byte[]]$info[0..(23636 - 17)])), [byte[]]$info[(23636 - 16)..(23636 - 1)])) { throw "info.bin's own MD5 does not match: start the game once first" }
    $ks = NvRc4 768
    $v = if ($on) { "1" } else { "0" }
    $coin = NvLoad $root $info "coin.xml" $ks
    $test = NvLoad $root $info "testmode-v.xml" $ks
    $was = $coin.text + "|" + $test.text
    NvSet $coin '(<freeplay __type="u8">)([01])(</freeplay>)' $v
    NvSet $test '(<freeplay>.*?<current __type="s32">)([01])(</current>)' $v
    if (($coin.text + "|" + $test.text) -ne $was) { NvSet $test '(<e_amusement>.*?<fixed __type="s32">)([01])(</fixed>)' "1" }   # the menu's save marks it; only when something is saved
    $l1 = [Text.Encoding]::GetEncoding(28591)
    $out = [ordered]@{}
    foreach ($p in @(@("coin.xml", $coin), @("testmode-v.xml", $test))) { $out[$p[0]] = NvXor ([byte[]]($l1.GetBytes($p[1].text) + $p[1].tail)) $ks }
    $textBytes = $l1.GetBytes($test.text)
    $crc = New-Object byte[] ([IO.File]::ReadAllBytes((Join-Path $root "0\testmode-v.crc")).Length)
    [BitConverter]::GetBytes([uint32](NvCrc32 $textBytes $textBytes.Length)).CopyTo($crc, 0)   # the text's size is exact: its zeros are not in it
    $out["testmode-v.crc"] = NvXor $crc $ks
    $changed = @()
    foreach ($name in $out.Keys) {
        $o = NvRecord $info $name
        $md5 = NvMd5 $out[$name]
        if (-not [Linq.Enumerable]::SequenceEqual($md5, [byte[]]$info[($o + 0x98)..($o + 0xa7)])) { $changed += $name; $md5.CopyTo($info, $o + 0x98) }
    }
    if (-not $changed) { return "" }
    foreach ($name in $changed) { foreach ($m in 0..3) { [IO.File]::WriteAllBytes((Join-Path $root "$m\$name"), $out[$name]) } }
    # the game stats every mirror file and compares it with its record (+0x18 per mirror: creation ms, write ms, size, u64 each; a mismatch
    # makes the module "broken" and every setting go back to its default): the record takes the files as they now are
    foreach ($name in $changed) {
        $o = NvRecord $info $name
        foreach ($m in 0..3) {
            $it = Get-Item -LiteralPath (Join-Path $root "$m\$name")
            $ms = @([DateTimeOffset]::new($it.CreationTimeUtc).ToUnixTimeMilliseconds(), [DateTimeOffset]::new($it.LastWriteTimeUtc).ToUnixTimeMilliseconds(), $it.Length)
            for ($k = 0; $k -lt 3; $k++) { [BitConverter]::GetBytes([uint64]$ms[$k]).CopyTo($info, $o + 0x18 * $m + 8 * $k) }
        }
    }
    (NvMd5 ([byte[]]$info[0..(23636 - 17)])).CopyTo($info, 23636 - 16)
    [IO.File]::WriteAllBytes((Join-Path $root "info.bin"), (NvXor $info (NvRc4 23636)))   # last: until then the old digests stand for the old files
    $changed -join ", "
}
# Before the game starts: the chosen Game mode's free play into the player's settings. Original has none: the player's own stay as they are.
# shortcut: with no settings yet (the very first start) nothing is written, the game makes them and the next start applies the mode.
function GameSettings($chosen) {
    $v = @($chosen | Where-Object { $_.PSObject.Properties["nvram"] })
    if (-not $v) { return }
    $root = Join-Path $mods "conf\nvram"
    if (-not (Test-Path -LiteralPath (Join-Path $root "info.bin"))) { Write-Host "game settings: none yet (the game makes them at its first start); Game mode applies from the next start"; return }
    try {
        $on = [bool]$v[0].nvram.freeplay
        $c = NvSetFreePlay $root $on
        Write-Host ("game settings: free play {0}{1}" -f $(if ($on) { "on" } else { "off" }), $(if ($c) { " (written: $c)" } else { " (already so)" }))
    } catch { Write-Host ("game settings: not changed ({0}); the game starts with the settings it has" -f $_) }
}

function Build {
    $sel = Eff   # shadows the choice: what is built, stamped and reported is what the game gets
    foreach ($o in $cat.options) { if ($sel[$o.id] -ne $script:sel[$o.id]) { Write-Host ("online: {0} held at Konami's value (a server is set)" -f $o.title) } }
    $chosen =@($cat.options | ForEach-Object { Val $_.id $sel[$_.id] })
    # "{option}" in a data folder's name is that option's value (eng_titles_{songs}: one per song list)
    foreach ($v in $chosen) {
        if ($v.PSObject.Properties["data"]) { $v.data = @($v.data | ForEach-Object { [regex]::Replace($_, "\{(\w+)\}", { param($m) $sel[$m.Groups[1].Value] }) }) }
    }
    $stamp = ((($cat.options | ForEach-Object { "{0}={1}" -f $_.id, $sel[$_.id] }) -join ",") + " " + (Md5 $catPath))
    $webcamDll = Join-Path $mods "webcam\Kinect10.dll"
    $stamp += " " + (Md5 (Join-Path $mods "bin\d3d9.dll")) + " " + (Md5 (Join-Path $mods "bin\spice.exe"))   # a new proxy with the same catalogue must reach the copy
    if ($chosen | Where-Object { $_.PSObject.Properties["sensor"] }) { $stamp += " " + (Md5 $webcamDll) }
    $stampPath = Join-Path $active "stamp.txt"
    if ((Test-Path -LiteralPath $stampPath) -and ((Get-Content -LiteralPath $stampPath -Raw).Trim() -eq $stamp)) { return $chosen }

    $bad = Altered
    if ($bad) { throw ("Not Konami's original: {0}. The mods are built on the original game only." -f ($bad -join ", ")) }
    if (Test-Path -LiteralPath $active) { Remove-Item -LiteralPath $active -Recurse -Force }
    New-Item -ItemType Directory $active | Out-Null
    Copy-Item -LiteralPath (Join-Path $root "modules") -Destination (Join-Path $active "modules") -Recurse
    Copy-Item -LiteralPath (Join-Path $mods "bin\spice.exe") -Destination (Join-Path $active "spice.exe")
    # a game copied from a disc, or extracted from an archive that kept the flag, is read-only, and so is its copy: the edits below could not be written
    Get-ChildItem -LiteralPath $active -Recurse -File | Where-Object { $_.IsReadOnly } | ForEach-Object { $_.IsReadOnly = $false }

    $files = @{}
    foreach ($v in $chosen) {
        foreach ($e in @($v.patches)) {
            if (-not $e) { continue }
            $path = Join-Path $active ("modules\" + $e.dllName)
            if (-not $files.ContainsKey($path)) { $files[$path] = [IO.File]::ReadAllBytes($path) }
            $b = $files[$path]
            $old = [byte[]]($e.dataDisabled -split '(..)' | Where-Object { $_ } | ForEach-Object { [Convert]::ToByte($_, 16) })
            $new = [byte[]]($e.dataEnabled -split '(..)' | Where-Object { $_ } | ForEach-Object { [Convert]::ToByte($_, 16) })
            for ($i = 0; $i -lt $old.Length; $i++) {
                if ($b[$e.offset + $i] -ne $old[$i]) { throw ("{0}+0x{1:x} does not hold the original bytes" -f $e.dllName, $e.offset) }
            }
            $new.CopyTo($b, $e.offset)
        }
    }
    foreach ($path in $files.Keys) { [IO.File]::WriteAllBytes($path, $files[$path]) }

    if ($chosen | Where-Object { $_.PSObject.Properties["laa"] }) {
        $exe = Join-Path $active "spice.exe"
        $b = [IO.File]::ReadAllBytes($exe)
        $pe = [BitConverter]::ToInt32($b, 0x3C)
        if ([BitConverter]::ToUInt32($b, $pe) -ne 0x4550) { throw "spice.exe is not a PE file" }
        $off = $pe + 4 + 18                          # COFF Characteristics
        $c = [BitConverter]::ToUInt16($b, $off) -bor 0x20   # LARGE_ADDRESS_AWARE
        [BitConverter]::GetBytes([uint16]$c).CopyTo($b, $off)
        [IO.File]::WriteAllBytes($exe, $b)
    }
    if ($chosen | Where-Object { $_.PSObject.Properties["env"] }) { Copy-Item -LiteralPath (Join-Path $mods "bin\d3d9.dll") -Destination $active }
    # the webcam sensor: our Kinect10.dll (Microsoft's stays in the game's own modules\); it starts mods\webcam\kdmsensor.exe
    # with the game and the game's end ends it. Beside spice.exe, as the proxy's d3d9.dll: the exe's folder is the
    # only one searched before the system's, and the Kinect runtime puts its Kinect10.dll in SysWOW64 (2026-10-31:
    # with ours only in modules\, the game got Microsoft's, no sensor started and it stopped at E7000).
    if ($chosen | Where-Object { $_.PSObject.Properties["sensor"] }) {
        Copy-Item -LiteralPath $webcamDll -Destination (Join-Path $active "Kinect10.dll") -Force
        Remove-Item -LiteralPath (Join-Path $active "modules\Kinect10.dll") -Force   # the copy's Microsoft one: spice2x warns of two Kinect10.dll
    }
    # The game opens its sound banks with CreateFileW, out of the hook's reach: the "Sound files"
    # option points it at mods\snd, filled here with hard links (no copies) to every original
    # file of data\sound, then the chosen mods' sound files over them.
    $snd = Join-Path $mods "snd"
    if (Test-Path -LiteralPath $snd) { Remove-Item -LiteralPath $snd -Recurse -Force }   # links only: the originals stay
    if ($chosen | Where-Object { $_.PSObject.Properties["sound"] }) {
        New-Item -ItemType Directory $snd | Out-Null
        foreach ($f in Get-ChildItem -LiteralPath (Join-Path $root "data\sound") -File) {
            SoundFile (Join-Path $snd $f.Name) $f.FullName
        }
        foreach ($v in $chosen) {
            if (-not $v.PSObject.Properties["data"]) { continue }
            foreach ($d in $v.data) {
                $src = Join-Path $mods "data\$d\sound"
                if (-not (Test-Path -LiteralPath $src)) { continue }
                foreach ($f in Get-ChildItem -LiteralPath $src -File) {
                    $dst = Join-Path $snd $f.Name
                    if (Test-Path -LiteralPath $dst) { Remove-Item -LiteralPath $dst -Force }
                    SoundFile $dst $f.FullName
                }
            }
        }
    }
    if ($chosen | Where-Object { $_.PSObject.Properties["data"] }) { Copy-Item -LiteralPath (Join-Path $mods "bin\ifs_hook.dll") -Destination (Join-Path $active "modules") }
    Set-Content -LiteralPath $stampPath -Value $stamp
    return $chosen
}

if ($Select) { foreach ($o in $cat.options) { $sel[$o.id] = $o.values[0].id } }   # -Select is the WHOLE selection
foreach ($kv in ($Select -split "," | Where-Object { $_ })) {
    $o, $v = $kv -split "="
    if (-not (Val $o $v)) { throw "no value '$v' for option '$o'" }
    Pick $o $v
}
if (-not $Select -and -not (Menu)) { exit 0 }
Save

$chosen = Build   # already built by the window's Play: the stamp makes this immediate
$data = @($chosen | Where-Object { $_.PSObject.Properties["data"] } | ForEach-Object { $_.data }) | Select-Object -Unique
$spiceArgs = @("-ea", "-io", "-modules", (Join-Path $active "modules"), "-v", "mods\conf\avs-config.xml", "-e", "mods\conf\eamuse-config.xml", "-y", "mods\conf\log.txt",
    "-cfgpath", (Join-Path $mods "conf\spicetools.xml"), "-patchcfgpath", (Join-Path $mods "conf\spice_patches.json"))
if ($data) { $spiceArgs += @("-k", "ifs_hook.dll", "--layered-data-mods-folder=./mods/data", ("--layered-allowlist=" + ($data -join ","))) }
if ($data -and $sel["verbose"] -eq "on") { $spiceArgs += "--layered-verbose" }   # the report: every file the mods served
foreach ($v in $chosen) { if ($v.PSObject.Properties["args"]) { $spiceArgs += @($v.args) } }
Write-Host ("built: {0}" -f $active)
$envs = @{}
foreach ($v in $chosen) {
    if ($v.PSObject.Properties["env"]) {
        foreach ($p in $v.env.PSObject.Properties) { $envs[$p.Name] = $p.Value -replace "\{mods\}", $mods }
    }
    if ($v.PSObject.Properties["sensor"]) { $envs["KDM_SENSOR"] = '"{0}" {1}' -f $sensorExe, (SensorArgs) }   # read by our Kinect10.dll
}
# What a server is told about this machine (T126; an honour label, not anti-cheat): the PCBID ends in "DE" + the sensor (0 Kinect, 1 camera)
# + the Song list (0 Konami's, 1 every song unlocked); the DEAC plugin reads it (ARCHITECTURE.md 16.11). trace.ps1 -Online takes the tail from launch.json.
$eff = Eff
$pcbidTail = "DE" + $(if ($eff["sensor"] -eq "webcam") { "1" } else { "0" }) + $(if ($eff["songs"] -eq "all") { "1" } else { "0" })
# The same mark in the model's revision letter (T146, ARCHITECTURE.md 16.21): every core hands a plugin the model (the official one hands no PCBID):
# D Kinect + Konami's Song list, E Kinect + every song, F camera + Konami's, G camera + every song. Konami's own letter is A.
$revMark = [string]"DEFG"[2 * [int]($eff["sensor"] -eq "webcam") + [int]($eff["songs"] -eq "all")]
@{ args = $spiceArgs; env = $envs; pcbid_tail = $pcbidTail; rev_mark = $revMark } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $active "launch.json")   # for trace.ps1 -Mods
# Only for a server on this PC or its own network (the DEAC plugin's core): a public network (RyuNET) knows the machine by the PCBID it
# registered, so that one is never changed, and its model is left as Konami's too (its own plugin is unread: the user decides when a public server
# is to get the mark). Offline the game keeps the player's p too. spice2x takes the settings FILE's p over a
# command-line -p (measured 2026-11-22: the game sent the file's), so the mark goes into a copy of the file in mods\active that -cfgpath points to;
# the revision letter goes into a copy of eamuse-config.xml the same way (-e), every other byte of it as shipped (latin-1 round trip).
# shortcut: a p that is not 20 hex characters is left alone (no mark is sent), not repaired.
if ((ServerUrl) -match '^https?://(localhost|127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)') {
    try {
        $l1 = [Text.Encoding]::GetEncoding(28591)
        $ea = $l1.GetString([IO.File]::ReadAllBytes((Join-Path $mods "conf\eamuse-config.xml")))
        $ea2 = [regex]::Replace($ea, '(<rev __type="str">)[^<]*(</rev>)', ('${1}' + $revMark + '${2}'))
        if ($ea2 -ceq $ea -and $ea -cnotmatch ('<rev __type="str">' + $revMark + '</rev>')) { throw "no <rev> in eamuse-config.xml" }
        $eaCopy = Join-Path $active "eamuse-config.xml"
        [IO.File]::WriteAllBytes($eaCopy, $l1.GetBytes($ea2))
        $spiceArgs[[array]::IndexOf($spiceArgs, "-e") + 1] = $eaCopy
    } catch { Write-Host ("online: could not mark the model ({0}); the server gets none that way" -f $_) }
    try {
        $x = New-Object Xml.XmlDocument; $x.Load((Join-Path $mods "conf\spicetools.xml"))
        $opt = $x.SelectSingleNode("//game[@name='Dance Evolution']/options/option[@name='p']")
        $p = if ($opt) { ([string]$opt.GetAttribute("value")).Trim() } else { "" }
        if ($p -match '^[0-9A-Fa-f]{20}$') {
            $opt.SetAttribute("value", $p.Substring(0, 16) + $pcbidTail)
            $copy = Join-Path $active "spicetools.xml"; $x.Save($copy)
            $spiceArgs[[array]::IndexOf($spiceArgs, "-cfgpath") + 1] = $copy
        } else { Write-Host "online: no valid PCBID (p) in spice2x settings, so the server gets no sensor or Song list mark" }
    } catch { Write-Host ("online: could not mark the PCBID ({0}); the server gets none" -f $_) }
}
Write-Host ("spice.exe {0}" -f ($spiceArgs -join " "))

# Windows Firewall. spice2x's e-amusement server listens on port 8080, so the first game on a PC raised Windows'
# "Allow access" prompt over the full-screen game, and that first game came up broken (the user, 2026-11-10, on the
# desktop). The game talks to it only through localhost, which the firewall never filters, so the network is not
# needed: the rule is there so Windows never asks. Allowed on private networks (what the prompt's Allow gives),
# blocked on public and domain ones (no prompt either, and no open port in a cafe). The only thing the launcher
# writes outside mods\ (the user's request, 2026-11-10). Our own group, rewritten when the folder moves.
function FirewallRules($exe) {
    if (-not (IsAdmin)) { return }
    $group = "DanceEvolution ARCADE launcher"
    try {
        $ours = @(Get-NetFirewallRule -Group $group -ErrorAction SilentlyContinue)
        $paths = @($ours | Get-NetFirewallApplicationFilter | ForEach-Object { $_.Program })
        if ($ours.Count -eq 2 -and @($paths | Where-Object { $_ -ne $exe }).Count -eq 0) { return }
        $ours | Remove-NetFirewallRule
        New-NetFirewallRule -Group $group -DisplayName "DanceEvolution ARCADE (spice2x), private networks" -Direction Inbound -Program $exe -Action Allow -Profile Private | Out-Null
        New-NetFirewallRule -Group $group -DisplayName "DanceEvolution ARCADE (spice2x), public networks" -Direction Inbound -Program $exe -Action Block -Profile Public, Domain | Out-Null
        Write-Host ("firewall: rules for {0}" -f $exe)
    } catch { Write-Host ("firewall: could not add the rules ({0}); Windows may ask on the first game" -f $_) }
}
FirewallRules (Join-Path $active "spice.exe")
GameSettings $chosen   # before the NoLaunch exit: trace.ps1 builds with -NoLaunch and then starts the game itself
if ($NoLaunch) { exit 0 }

# Before: the game's files are Konami's (the window checked them when it opened; -Select has no window).
$title = "DanceEvolution ARCADE"
$bad = if ($Select) { Altered } else { @() }
if ($bad) { throw ("These game files are not Konami's originals: {0}. Restore them from your copy of the game before playing." -f ($bad -join ", ")) }
$cams = if ($chosen | Where-Object { $_.PSObject.Properties["sensor"] }) { @(Cameras) } else { $null }
if ($null -ne $cams -and -not ($cams -contains $camera -or (-not $camera -and $cams.Count))) {
    throw "Body sensor is a webcam, but the camera '$camera' is not connected. Plug it in, or choose another camera in the launcher."
}

foreach ($k in $envs.Keys) { Set-Item ("env:" + $k) $envs[$k] }
$env:DAMAC_VIEWER_FULLSCREEN = "1"
foreach ($d in @("conf\raw\log", "conf\nvram")) { New-Item -ItemType Directory -Force (Join-Path $mods $d) | Out-Null }
Set-Location -LiteralPath $root
$exe = Join-Path $active "spice.exe"
$started = Get-Date
$game = [Diagnostics.Process]::Start((New-Object Diagnostics.ProcessStartInfo -Property @{ FileName = $exe; UseShellExecute = $false; WorkingDirectory = $root
    Arguments = (($spiceArgs | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join " ") }))
ForegroundGame $game
$game.WaitForExit()
$code = $game.ExitCode
# The game's end kills the sensor through its job, before it can put the camera's own exposure and gain back (its low-light step,
# camera.h): the sensor left what it found in mods\webcam\camera_restore.txt, and this puts it back.
if (Test-Path -LiteralPath (Join-Path $mods "webcam\camera_restore.txt")) { & $sensorExe --restore-camera | Out-Null }

# After: wait until nothing of the game is left running (a crash can take seconds to unwind), then check
# the game's files again, so the player knows the next game can start and that nothing was damaged.
$deadline = (Get-Date).AddSeconds(60)
while ((Get-Process | Where-Object { $_.Path -and $_.Path.StartsWith($root, [StringComparison]::OrdinalIgnoreCase) }) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 500 }
$left = @(Get-Process | Where-Object { $_.Path -and $_.Path.StartsWith($root, [StringComparison]::OrdinalIgnoreCase) })
$bad = Altered
$problems = @()
if ($code) { $problems += "The game stopped with an error (code {0})." -f $code + $(if ($sel["verbose"] -ne "on") { " To report it: set Advanced > Diagnostic log to Full log and report, and play again." }) }
if ($bad) { $problems += "These game files are no longer Konami's originals: {0}." -f ($bad -join ", ") }
if ($left) { $problems += "Still running: {0}. Close it (Task Manager) before playing again." -f (($left | ForEach-Object { $_.ProcessName }) -join ", ") }
$report = if ($sel["verbose"] -eq "on") { try { "`r`n`r`nReport saved, please send it back:`r`n" + (Report $chosen $code $started) } catch { "`r`n`r`nThe report could not be saved: $_" } } else { "" }
if ($problems) { [void][Windows.Forms.MessageBox]::Show(($problems -join "`r`n`r`n") + $report, $title, "OK", "Warning") }
else { [void][Windows.Forms.MessageBox]::Show("All good: the game closed normally and its files are untouched. You can play again." + $report, $title, "OK", "Information") }
