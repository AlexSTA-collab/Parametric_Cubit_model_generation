#!/bin/bash
set -Eeuo pipefail
IFS=$'\n\t'

# ---------------------------
# User options
# ---------------------------
PNG_DIR="Relaxation_stiff_Interface"
LOGO="logo.png"
REPEATS=6
FRAMERATE=10
OUTPUT="smooth_loop_relaxation_interface_stiff.mp4"
CRF=18
PRESET="slow"

# ---------------------------
# Debug logger
# ---------------------------
log() { echo -e "\033[1;34m[DEBUG]\033[0m $*"; }

# ---------------------------
# Dependencies
# ---------------------------
log "Checking dependencies..."
command -v ffmpeg >/dev/null || { echo "❌ ffmpeg not found"; exit 1; }
command -v identify >/dev/null || { echo "❌ ImageMagick not found"; exit 1; }
log "Dependencies OK."

# ---------------------------
# Find first PNG
# ---------------------------
log "Searching for first PNG in $PNG_DIR ..."
FIRST_PNG=$(find "$PNG_DIR" -type f -name '*.png' | sort | head -n 1)
if [[ -z "$FIRST_PNG" ]]; then
  echo "❌ No PNGs found in $PNG_DIR"
  exit 1
fi
log "First PNG: $FIRST_PNG"

# ---------------------------
# Get resolution safely
# ---------------------------
RES=$(identify -format "%w %h" "$FIRST_PNG" | tr -d '\r')
WIDTH=$(echo "$RES" | awk '{print $1}')
HEIGHT=$(echo "$RES" | awk '{print $2}')
WIDTH=$(( WIDTH / 2 * 2 ))
HEIGHT=$(( HEIGHT / 2 * 2 ))
log "Detected resolution: ${WIDTH}x${HEIGHT}"

# ---------------------------
# Count frames
# ---------------------------
NUM_FRAMES=$(find "$PNG_DIR" -type f -name '*.png' | wc -l)
log "Found $NUM_FRAMES frames in $PNG_DIR"

# ---------------------------
# Create base video
# ---------------------------
log "Creating base video..."
CMD1=(
  ffmpeg -hide_banner -y
  -framerate "$FRAMERATE"
  -i "${PNG_DIR}/Relaxation_interface_stress.%04d.png"
  -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=rgba"
  -c:v libx264 -pix_fmt yuv420p -crf "$CRF" -preset "$PRESET"
  single.mp4
)
log "Running: ${CMD1[*]}"
"${CMD1[@]}"

if [[ ! -s single.mp4 ]]; then
  echo "❌ Failed to create single.mp4"
  exit 1
fi
log "Base video created."

# ---------------------------
# Loop & overlay logo
# ---------------------------
if [[ -f "$LOGO" ]]; then
  log "Looping $REPEATS× and adding logo..."
  CMD2=(
    ffmpeg -hide_banner -y
    -stream_loop $((REPEATS-1))
    -i single.mp4
    -i "$LOGO"
    -filter_complex "[1:v]scale=128:128[logo];[0:v][logo]overlay=x=W-w-10:y=H-h-10"
    -c:v libx264 -pix_fmt yuv420p -crf "$CRF" -preset "$PRESET"
    "$OUTPUT"
  )
else
  log "Looping $REPEATS× (no logo)..."
  CMD2=(
    ffmpeg -hide_banner -y
    -stream_loop $((REPEATS-1))
    -i single.mp4
    -c:v libx264 -pix_fmt yuv420p -crf "$CRF" -preset "$PRESET"
    "$OUTPUT"
  )
fi

log "Running: ${CMD2[*]}"
"${CMD2[@]}"

# ---------------------------
# Cleanup
# ---------------------------
rm -f single.mp4

if [[ -s "$OUTPUT" ]]; then
  log "✅ Done! Created: $OUTPUT"
  log "   Resolution: ${WIDTH}x${HEIGHT}"
  log "   Looped: $REPEATS× at ${FRAMERATE} FPS"
else
  echo "❌ Something went wrong — no output created."
  exit 1
fi

