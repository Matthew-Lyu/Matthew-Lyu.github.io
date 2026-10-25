# Local builds/preview use the same optimizer as the deployment workflow.
Jekyll::Hooks.register :site, :post_write do |site|
  next if ENV['SKIP_COVER_PREVIEWS'] == '1'

  script = File.join(site.source, 'scripts', 'optimize-covers.py')
  python = ENV.fetch('PHOTO_PYTHON', 'python3')
  success = system(python, script, '--source', site.source,
                   '--destination', site.dest, '--baseurl', site.config['baseurl'].to_s)
  unless success
    raise Jekyll::Errors::FatalException,
          'Image preview generation failed. Run ./preview.command to prepare the image dependencies.'
  end
end
