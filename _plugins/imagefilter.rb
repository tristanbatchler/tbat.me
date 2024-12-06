require 'fastimage'
require 'uri'
require 'pathname'

module ImageSizeFilter
  def image_size(source, dimension = nil)
    # If source starts with a '/', it's a URL. Resolve it to a local file path.
    if source.start_with?('/', 'http')
      # For local development, _site is where your built files are
      source = File.join(Dir.pwd, '_site', source.sub(/^\//, ''))
    end

    # Check if the file exists on the filesystem
    if File.exist?(source)
      begin
        # Get image dimensions using FastImage
        size = FastImage.size(source, raise_on_failure: true)

        # Return the requested dimension, or both dimensions if nothing was specified
        return size[0] if dimension == 'w'
        return size[1] if dimension == 'h'
        return size unless dimension
      rescue FastImage::ImageFetchFailure => e
        raise "Unable to fetch image size for: #{source}. Error: #{e.message}"
      end
    else
      raise "Image not found: #{source}"
    end
  end
end

Liquid::Template.register_filter(ImageSizeFilter)
