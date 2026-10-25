#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "$0")"

project_dir="$PWD"
tools_dir="$project_dir/vendor/tools"
bundler_version="2.4.22"
bundler_lib="$tools_dir/gems/bundler-$bundler_version/lib"
bundler_exe="$tools_dir/gems/bundler-$bundler_version/exe/bundle"

# Use a project-local Bundler, including on macOS with Ruby 2.6 / Bundler 1.x.
if [ ! -f "$bundler_exe" ]; then
  mkdir -p "$tools_dir/cache"
  gem_file="$tools_dir/cache/bundler-$bundler_version.gem"
  curl -fL --retry 2 "https://rubygems.org/downloads/bundler-$bundler_version.gem" -o "$gem_file"
  gem install --local "$gem_file" --install-dir "$tools_dir" --no-document
fi

export BUNDLE_PATH="$project_dir/vendor/bundle"
run_bundle() { ruby -I "$bundler_lib" "$bundler_exe" "$@"; }
if ! run_bundle check >/dev/null 2>&1; then
  run_bundle install
fi

# Image dependencies are prepared once; cover previews regenerate with Jekyll.
image_python="${PHOTO_PYTHON:-python3}"
if ! "$image_python" -c 'from PIL import Image, features; assert features.check("webp")' >/dev/null 2>&1; then
  image_python="$tools_dir/image-python/bin/python"
  if [ ! -x "$image_python" ]; then
    python3 -m venv "$tools_dir/image-python"
  fi
  "$image_python" -m pip install -r "$project_dir/scripts/requirements-images.txt"
fi
export PHOTO_PYTHON="$image_python"

requested_port="${PORT:-4000}"
preview_port="$(ruby -rsocket - "$requested_port" <<'RUBY'
requested = ARGV.fetch(0)
unless requested.match?(/\A[0-9]+\z/) && requested.to_i.between?(1, 65_535)
  abort "PORT must be an integer between 1 and 65535."
end

first = requested.to_i
(first..[first + 49, 65_535].min).each do |port|
  begin
    server = TCPServer.new('127.0.0.1', port)
    server.close
    puts port
    exit
  rescue Errno::EADDRINUSE
    next
  end
end
abort "No available preview port found. Try PORT=5000 ./preview.command."
RUBY
)"
if [ "$preview_port" != "$requested_port" ]; then
  printf '\nPort %s is in use; switching to %s.\n' "$requested_port" "$preview_port"
fi
printf '\nPreview: http://127.0.0.1:%s/\nStop: Ctrl+C\n\n' "$preview_port"
exec ruby -I "$bundler_lib" "$bundler_exe" exec jekyll serve --host 127.0.0.1 --port "$preview_port" --force_polling
