# Changelog

The newest version first. A release's notes are its section of this file, and are what the launcher shows before an update.

## 1.0.0

The first public release. It carries every change made since the first pack (3 November 2026).

**The launcher**
- Looks for a newer release each time it opens and shows what changed, with Update and Not now. An update downloads only the parts that changed, checks every file's SHA-256 and replaces nothing until all are right; a failed or cut-short download leaves the version you have.
- Delivered as a release of this repository plus one separate file, `KDMSENSOR-restored-audio.7z` (the audio no Konami base holds), put in `mods` once and checked by SHA-256. Everything else is made on your PC from your own game files and checked against the release's list before it is written, with a private Python: nothing to install.
- Runs its own spice2x, keeps every setting, save and log in `mods\`, and writes nothing outside it except two Windows Firewall rules for its copy of spice2x (private networks allowed, public blocked) so Windows never interrupts the first game.
- Works on a Windows in any language and in a folder with any name (the administrator check was by the group's English name and looped on other languages; paths with `[` or `]`; two non-ASCII characters in the script).
- Checks that every game file the mods could touch is Konami's before and after each game, in pieces so the window answers; names the DirectX runtime (June 2010) when Windows lacks it; ignores a damaged `selection.json`; copes with a read-only game.
- Online, the game obeys the server: with an e-amusement server set, the options that change judging or score (Stealth as Master, Game mode, Songs per game) stay at Konami's value and show greyed. Your Song list and sensor are told to the server.
- The controls button is named for what it opens (spice2x settings...).

**Content**
- Every song unlocked: the 22 songs Konami's last offline build locked, the 20 audio banks it emptied restored, YESTERDAY added (102 songs), a song-select preview for every song with Konami's own fade-out, licensed songs filed under POPULAR and Konami's under KONAMI SONGS as Konami filed them, the `rena` typo fixed.
- Language: English, Traditional Chinese or Japanese; English and romanised song titles with the NAME tab running A to Z.
- Stealth played as Master on the 30 Dance Masters songs.
- Test mode's screen check scaled at every resolution.

**Game rules**
- Game mode: credits, free play, event mode. Songs per game: 1 to 4.

**Picture**
- Native 1080p, 1440p and 2160p (3D, effects, 2D and the camera picture; 1440p and 2160p were not played on a screen of that size), unlimited frame rate with the menus at the cabinet's speed, SMAA, anisotropic x16, render threads.

**Attract demo**
- Master charts, whole songs, every song shuffled, score and combo displayed.

**Body sensor**
- The webcam sensor: any camera (built-in, USB, phone apps, virtual cameras, capture cards) read as a Kinect would, on the graphics card in real time, with an automatic six-step calibrator that finds the camera's height and tilt and sets the hand cursor for any player's height. Kinect v1 still works as the game was made.
- Camera warnings for filters and effects, Windows Studio Effects switched off for the session, the camera's own exposure put back after the game.
