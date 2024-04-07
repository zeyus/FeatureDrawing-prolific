# Make all gifs in specified directory loop inifinitely using imagemagick

# Usage: make_gifs_loop.ps1 [-m <magick_bin>]  <directory>

param(
    [string]$magick_bin = "magick.exe",
    [switch]$dry_run = $false,
    [string]$directory = "." # current directory
)

# make sure directory exists
if (-not (Test-Path $directory)) {
    Write-Host "Directory $directory does not exist"
    exit
}

# test if magick is installed
if (-not (Test-Path $magick_bin)) {
    Write-Host "Magick not found at $magick_bin"
    exit
}

# get all gifs in directory
$gifs = Get-ChildItem -Path $directory -Filter *.gif

# warn if no gifs found
if ($gifs.Count -eq 0) {
    Write-Host "No gifs found in $directory"
    exit
}

# notify if dry run
if ($dry_run) {
    Write-Host "Dry run, no gifs will be looped"
}


# loop through all gifs
foreach ($gif in $gifs) {
    # loop gif
    $cmd = "&""$magick_bin"" mogrify -background white -alpha background -alpha off -loop 0 ""$gif"""
    if ($dry_run) {
        Write-Host $cmd
    } else {
        Write-Host "Looping $gif"
        Invoke-Expression $cmd
    }
}