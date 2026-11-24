
    DANCEEVOLUTION ARCADE  -  THE MODS PACK
    for the base game KDM-001-2016080100

    One launcher with every mod as an option, and a body sensor that
    works with a Kinect or with any webcam. The game itself is never
    changed: with every option on "Original" it is Konami's game exactly
    as it shipped.

    Open source: github.com/Cris-Oblea/KDMSENSOR (the source, every
    release and its changes; anyone may read it, report a problem or
    fork it). The launcher links it below its buttons. For a server,
    the game's own Asphyxia plugin: github.com/Cris-Oblea/asphyxia-deac


    CONTENTS

      1.  Quick start
      2.  Updating from an earlier pack
      3.  The launcher window
      4.  The body sensor: Kinect or webcam
      5.  Calibrating a webcam
      6.  The options, one by one
      7.  If something goes wrong
      8.  Using it beside other mods
      9.  What is in the pack
     10.  Removing it


========================================================================
 1.  QUICK START
========================================================================

  You need

    - Your own copy of the game: DanceEvolution ARCADE, the August 2016
      build, KDM-001-2016080100, extracted and unmodified. The game is
      not in this pack and we do not share it.
    - Windows 10 or 11, in any language.
    - Microsoft's "DirectX End-User Runtimes (June 2010)". The game
      needs it and Windows does not bring it. If you already play
      this game, you have it; if not, the launcher says so beside
      Play.
    - A Kinect v1, or a camera (section 4). For a camera: 64-bit
      Windows and a graphics card with DirectX 12.

  Install

    Download the latest KDMSENSOR-x.y.z.zip from the project's Releases
    page (github.com/Cris-Oblea/KDMSENSOR/releases) and extract it into
    the base game's folder, the one that holds "data", "modules" and
    "prop". It adds three things and touches nothing else:

        1 - Play.bat             the launcher
        1 - Play (README).txt    this file
        mods\                    everything the launcher uses

    The first time you open the launcher it needs one more file, which
    you put in the mods folder yourself: KDMSENSOR-restored-audio.7z,
    about 95 MB (the songs' restored audio, which no game folder holds).
    The launcher says so if it is missing, checks it, and makes the rest of the mods
    from YOUR game files, about a minute. If your game files are not
    Konami's August 2016 build it says so and writes nothing. From then
    on it works offline, and each time it opens it looks for a newer
    release (section 2).

    Keep the game on a drive of the PC itself, not a network drive
    (section 7 says why).

  Play

    1.  Open "1 - Play.bat" and say yes to the administrator prompt.
        The launcher's window opens a few seconds later.
    2.  First time only: press "spice2x settings..." and bind your buttons.
        The cabinet has no keyboard, so nothing is bound by default.
        Bind at least Test, Service, P1 Start, P1 Left and P1 Right.
    3.  Choose your options. Click any of them and the window explains
        it. Your choices are saved for next time.
    4.  With a webcam: choose it under "Body sensor" and press
        "Calibrate camera..." once (section 5).
    5.  Press "Play".

  The very first boot may stop on an error screen: the machine's clock
  is not set yet. Close the game and start it again.


========================================================================
 2.  UPDATING
========================================================================

  From a release (version 1.0.0 on)

      Every time it opens, the launcher looks at the project's latest
      release. If it is newer, a window lists what changed, with
      "Update" and "Not now". Update downloads only the parts that
      changed, checks every file against the release's SHA-256, and
      only then replaces them; if the internet drops or a file is
      wrong, nothing is replaced and you keep the version you had.
      Your options, buttons, saves and calibration are never touched,
      and neither is Konami's game. Offline, it just opens.

      To look for an update without reopening the launcher, press
      "Check for updates" beside Play. It makes the same look and
      answers in a window: you have the latest version, no internet, or
      no release published yet; a newer version opens the same window.
      It waits while the controls, a preview or the camera calibration
      are open.

      The launcher's title shows the version you have. Below its
      buttons, the project's GitHub page and the "Changelog" link, which
      opens every version's changes.

  You have a pack of the earlier kind, with "1 - Play.bat" and a
  "mods" folder (November 2026)

      Extract the first release over it and say yes to replacing files.
      It is safe: the pack holds no settings. Your buttons, your saves
      and your chosen options stay as they are.

      After updating:

        - With a webcam, press "Calibrate camera..." once more, and
          check that "Webcam sensor runs on" says GPU.
        - If the launcher asks, bind your buttons again.
        - You can delete "mods\README.txt": this file replaces it.

  You have our older build (September 2026, no "mods" folder), or any
  mod that changed the game's own files

      Do not extract over it. Those builds changed Konami's files, and
      this launcher only starts on the original ones: it would name the
      changed file and refuse to play.

      Start clean: extract the base game again into a new folder, then
      extract this pack into it. Mods that only add their own folders
      and leave Konami's files alone can stay (section 8).


========================================================================
 3.  THE LAUNCHER WINDOW
========================================================================

  Play
      Builds the game with your options and starts it. The label beside
      the button says whether the game's files are Konami's originals.
      They are checked before and after every game.

  spice2x settings...
      Opens spice2x's own settings window: your cards, patches,
      options and buttons (bind your keys or pad here). Its
      Options tab also holds the e-amusement server's URL (for online
      play). With a server set, the options that change the score
      (Stealth difficulty, Songs per game) stay at Konami's
      value and show greyed: online, the game is the server's. Clear
      the URL and they work again.

  Sensor preview...
      Shows the chosen sensor live: the picture, the skeleton, and the
      player the game will get. Close it before pressing Play.

  Calibrate camera...   (webcam only)
      The automatic calibrator. See section 5.

  Advanced...           (webcam only)
      The calibrator's numbers, to fine-tune by hand. You never need it.

  The game always opens in exclusive full screen with vsync.


========================================================================
 4.  THE BODY SENSOR: KINECT OR WEBCAM
========================================================================

  Kinect (original)
      A Kinect v1 with Microsoft's runtime, as the game was made.

      Mount it high, about 2 metres, looking down. The song selector is
      driven by your raised hand, and a low Kinect never sees it.
      Never tilt a Kinect v1 by hand: use "Sensor preview..." and the
      arrow keys.

  Webcam or any camera
      The pack's own sensor turns the camera's picture into the skeleton
      the game expects from a Kinect. There is nothing to install or
      open: it starts and stops with the game. It runs on the graphics
      card in real time, 30 skeletons a second, the same as a Kinect.

      Place the camera facing you, with your whole body in the picture,
      feet included, and light on you.

      Camera
          Which camera to use. The list holds every camera Windows
          has, by both of its camera systems, and the launcher refuses
          none of them:

            - built-in cameras, USB webcams, capture cards;
            - a phone used as a webcam, by USB or Wi-Fi, through its
              program on the PC (DroidCam, Iriun, iVCam, Camo...);
            - virtual cameras (OBS Virtual Camera and the like).

          If a camera's program is installed but its camera is not in
          the list, start that program first and open the launcher
          again. A very old 32-bit-only virtual camera cannot be read.
          OBS Virtual Camera sends a picture only while OBS is open
          with "Start Virtual Camera" on.

          Played with: a notebook's built-in camera and a USB webcam.
          Seen working in the sensor preview: an Android phone through
          DroidCam over Wi-Fi, and OBS Virtual Camera. Camo (for an
          iPhone) installs a camera the list shows and reads at 30
          pictures a second; it was tried without an iPhone. Tell us
          how yours went.

          With any camera, switch off every filter and effect:
          background blur or replacement, beauty filters, automatic
          framing, zoom. They change the body the sensor reads, and
          the game then judges you badly.

          For four programs known for such effects (OBS Virtual Camera,
          NVIDIA Broadcast, XSplit VCam, Snap Camera) the launcher
          writes a red reminder under the camera. It is only a
          reminder: you can still calibrate and play.

          The dim-room exposure step and the Windows Studio Effects
          switch below work on real cameras, not on virtual ones.

      Windows Studio Effects
          Background blur, eye contact and automatic framing are
          switched off for the session. If one refuses, the launcher
          names it and says where Windows turns it off.

      Dim rooms
          The sensor sets the camera's exposure so it keeps 30 pictures
          a second, and puts your camera's settings back after the game.

      Webcam sensor runs on
          GPU (DirectML; the CPU if the GPU cannot run it)  |  CPU
          Leave it on GPU: it is faster and leaves the CPU to the game.
          If the graphics card cannot run it, the sensor uses the CPU
          by itself.


========================================================================
 5.  CALIBRATING A WEBCAM
========================================================================

  Press "Calibrate camera..." once, where you play. It takes about a
  minute. Nothing is typed and nothing is measured with a tape.

  The window shows the pose to make, counts down, and tells you whether
  it was good. A step that fails says why and repeats.

    Step 1   Stand where you play, whole body and feet in the picture.
    Step 2   Stand still, arms down.
    Step 3   Take one big step straight back and stand still again.
    Step 4   Raise both arms.
    Step 5   Right arm straight out to the side, then straight up.
    Step 6   Crouch, as you would in a song.

  What it sets up for you:

    - the camera's height and tilt;
    - the game's view, so your feet and raised hands stay in sight;
    - the hand cursor: your arm at shoulder height drives the song
      selector and your raised arm reaches OK;
    - a check that the game does not lose you when you crouch;
    - whether two players fit in your room, and how far back to stand.

  Good to know:

    - It works for players of any height. An adult should do the
      calibration; after that anyone can play.
    - If other people are in the picture it reads the nearest one.
    - Calibrate again when you move the camera or change rooms.


========================================================================
 6.  THE OPTIONS, ONE BY ONE
========================================================================

  The first choice of every option is the original game.


  CONTENT
  -------

  Language
      Japanese (original)  |  English  |  Chinese (Traditional)
      Every text and menu picture, from the game's own assets.

  Song list
      Original (78 songs)  |  Every song unlocked (101 songs)
      Konami's last offline build locked 22 songs and emptied the audio
      of 20 of them. This brings them all back, adds YESTERDAY, and
      gives a song-select preview to every song that had none:
      Konami's own from its February 2016 build where it exists, and
      for YESTERDAY, which never had one, a cut with Konami's fade.
      In song select the licensed songs go under POPULAR and Konami's
      under KONAMI SONGS, as Konami filed them. The arcade has no genre
      tabs (POP, PARA PARA...): those were the home version's.

  Song titles in English
      Original  |  English and romanised
      Writes the Japanese titles and artists in Latin letters, with
      each song's official English or romanised name. Switches the
      language to English. With it, the NAME tab in song select runs
      A to Z by these titles; without it, NAME keeps Konami's order,
      by the titles' Japanese reading.

  Stealth difficulty
      Original  |  Stealth = master everywhere
      Stealth is the hardest chart with no step markers. On the 30 songs
      from the Dance Masters disc it copied EXTREME; this makes it copy
      MASTER, as it does on the arcade's own songs.
      Only those 30 songs change, and only on Stealth. Their Stealth
      scores are then scores of the MASTER chart: do not compare them
      with players who keep Original, and keep Original yourself if
      your scores go to a shared ranking.


  GAME RULES
  ----------

  Game mode
      Original (your game's settings)  |  Credits  |  Free play  |
      Event mode (free play, clocks frozen)
      How a game is paid and timed, set as the arcade's operator sets it
      (it works online too). Credits and Free play are saved in your game's
      settings. Event mode has no time limit and no game over between songs.

  Songs per game
      Original (the service menu's setting)  |  1 song  |  2 songs  |
      3 songs  |  4 songs
      How many songs one game gives.


  PICTURE
  -------

  Resolution
      1280x720 (original)  |  1920x1080 native  |  2560x1440 native  |
      3840x2160 native
      Rendered natively: 3D, effects, 2D and the camera picture. It is
      not an upscale. Only the sizes your main screen has are listed.
      4K was played on a 4K TV; 1440p was never played on a screen of
      that size: please tell us how it looks.

  Frame rate
      Original: what Konami's game asks for
          Nothing changed: the game asks for 60 Hz.
      Unlimited: up to your monitor's maximum
          As many frames as the PC can draw, up to the monitor's
          highest rate. The song and difficulty select keep the
          cabinet's speed (above 60 fps the original ones run too
          fast).
      Limit to 60 fps
          Stability over frames. Choose it if Unlimited and the webcam
          sensor together give you trouble, or to keep a notebook cool.
      Vsync is always on and the songs stay in sync at any frame rate.
      You never need to change your monitor's Hz. Before playing, close
      Task Manager and anything set to stay on top, on any screen: it
      makes the game lose frames.

  Anti-aliasing
      Off (original)  |  SMAA
      Smooths the jagged edges of the 3D.

  Texture filtering
      Original  |  Anisotropic x16
      Keeps floors and walls sharp at a glancing angle.


  ATTRACT DEMO   (what the cabinet plays while nobody does)
  ------------

  Attract demo: difficulty
      Original  |  Master charts
      Original plays the standard charts.

  Attract demo: length
      Original (30 s)  |  Whole songs
      Original stops each demo song after 30 seconds.

  Attract demo: song order
      Original  |  Every song, shuffled, none twice per round
      Original plays two fixed playlists.

  Attract demo: score display
      Original  |  Score and combo
      Shows the SCORE bar and the COMBO, as in real play.


  ADVANCED
  --------

  Render threads
      Original (1 thread)  |  Sized to the CPU
      Smoother songs on a fast monitor.

  Diagnostic log
      Off  |  Full log and report
      For reporting a problem. See section 7. The game starts slower
      with it: leave it off to play.


  ALWAYS ON, NOT IN THE MENU
  --------------------------

    - 4 GB memory limit, on the launcher's own copy of spice.exe. With
      the original 2 GB the game runs out of memory on a modern PC and
      crashes.
    - More sound memory and the sound folder "mods\snd", switched on by
      "Every song unlocked", which needs them.
    - The ranking event's RANKING! icon. When a server runs a ranking
      event (two songs everyone competes on), the game was meant to mark
      those songs' difficulties with it in the difficulty select, but
      Konami's build never loads the file that holds the picture. This
      loads it. It changes no score, so it is fine on a server too;
      without an event nothing is drawn.
    - Two Windows Firewall rules for the launcher's copy of spice.exe
      (allowed on private networks, blocked on public ones), so Windows
      never interrupts the first game to ask. It is the only thing the
      pack writes outside "mods".


========================================================================
 7.  IF SOMETHING GOES WRONG
========================================================================

  Nothing opens after the administrator prompt
      - The first pack (11 November 2026) did this on a Windows whose
        own language is not English: Russian, Spanish, German...
        Fixed in this pack, and confirmed by the player who found
        it. If it happened to you, restart Windows once (the old
        launcher may still be running hidden), then extract this
        pack over the old one.
      - The game is on a network drive or a "subst" drive letter:
        Windows hides those from a program run as administrator.
        Move the game to a drive of the PC itself.

  "mods\ is missing from this folder"
      The pack was opened from inside the archive, or extracted
      somewhere else. Extract it into the base game's folder, beside
      "data" and "modules".

  Play stays off: "Missing: DirectX runtime (June 2010)"
      Install Microsoft's "DirectX End-User Runtimes (June 2010)" and
      open the launcher again.

  An antivirus removes or blocks a file
      The launcher makes its own copy of spice.exe in "mods\active"
      at every change of options, and some antivirus programs distrust
      a new program. Allow the game's folder in it. Windows'
      "Controlled folder access" blocks the launcher from writing in
      Documents or Desktop: keep the game elsewhere, or allow it.

  A phone's camera shows a plain green picture
      The phone's program is not passing its video on: Windows' own
      Camera app shows the same green. Seen with DroidCam just after
      installing it: in its PC client use File > Exit, open it again
      and reconnect (or restart the PC), then open the launcher.

  The camera is listed but does not open
      Windows Settings > Privacy & security > Camera: "Let desktop
      apps access your camera" must be on. Close any other program
      that is using the camera. On a Windows "N" edition, install
      Microsoft's Media Feature Pack: the sensor needs it.

  The launcher works but the game never appears
      Try the game in a short folder named with English letters only,
      for example C:\Games\DEA. The launcher itself accepts any
      folder name; we have not tried the 2016 game in every one.

  The first boot stops on an error screen
      Normal: the clock is not set. Close the game and start it again.
      To set it: Test -> CLOCK.

  Play stays off and the label names a file
      Another mod edited one of Konami's files in place. Restore that
      file from the base game.

  The game closes at once with no message
      Windows Smart App Control can block the launcher's copy of
      spice.exe. It has to be off.

  Play says the camera is missing
      Choose it again under "Camera", and close any app that is using
      it.

  The game loses you, or the hand cursor does not reach
      Check "Sensor preview...", then calibrate again.

  To report a problem
      Set "Diagnostic log" to "Full log and report" and play again.
      When the game closes, a zip is saved in "mods\reports", with your
      Windows user and PC names removed. Send us that zip.


========================================================================
 8.  USING IT BESIDE OTHER MODS
========================================================================

  The pack runs its own spice2x from "mods\bin" and keeps its settings,
  patches, saves and log in "mods\conf". It writes nothing into "data",
  "modules" or "prop".

  Whatever you used before keeps working exactly as it was: open that
  launcher or this one, as you like. Your other mods are not loaded
  when you play from here.


========================================================================
 9.  WHAT IS IN THE PACK
========================================================================

  1 - Play.bat             the launcher
  1 - Play (README).txt    this file
  mods\play_mods.ps1       the launcher's program
  mods\update.ps1          its updater and first-run setup
  mods\catalog.json        every option and exactly what it changes
  mods\version.json        the installed version and every file's SHA-256
  mods\bin\                spice2x, the mod loader, the picture filters,
                           7zr.exe (7-Zip) and a private Python (python\)
  mods\generator\          the program that makes the mods from your game
  mods\generated.json      what it must make, file by file (SHA-256)
  mods\fixed.json          the restored audio's name, size and SHA-256
  mods\webcam\             the webcam sensor and its models

  Made on your PC, and yours to keep:

  mods\data\               the songs, previews, titles and shaders
  mods\conf\               the game's configuration, your buttons and saves
  mods\fixed\              the restored audio's own files
  mods\setup.json          what the first run has already done
  mods\active\             the game built with your options
  mods\snd\                the sound folder for the unlocked songs
  mods\selection.json      your options and your calibration
  mods\reports\            the diagnostic reports

  Where the restored songs come from: of the 20 emptied audio banks,
  14 are Konami's own audio, as in its October 2015 build. The other
  6 (brav, iron, maru, merr, noff, rena) and YESTERDAY's audio and
  jacket are found only in a copy of the February 2016
  build that circulates since 2017; they come in the one-time download. We do not know who put them there
  or where that audio came from; if you do, tell us and we will
  credit them. YESTERDAY's chart data is from the Dance Masters disc.


========================================================================
10.  REMOVING IT
========================================================================

  Delete "1 - Play.bat", "1 - Play (README).txt" and the folder "mods".
  The game is left exactly as it was. The two firewall rules stay in
  Windows Firewall under "DanceEvolution ARCADE launcher": delete them
  there if you like.
