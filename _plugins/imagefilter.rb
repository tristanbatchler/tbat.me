require 'fastimage'

module ImageSizeFilter
  def image_size(source, dimension = nil)
    puts "supplied source: #{source}"

    # Check if the source is a URL
    is_url = source.start_with?('http://', 'https://')

    puts "is_url: #{is_url}"

    # If it's not a URL, resolve it to a local file path
    unless is_url
      # For local development, use the `_site` folder as the base
      source = File.join(Dir.pwd, '_site', source.sub(/^\//, ''))
      puts "was not a url, so updated source: #{source}"
    end

    # Get image dimensions using FastImage
    begin
      size = FastImage.size(source, raise_on_failure: true)

      # Return the requested dimension or both dimensions
      return size[0] if dimension == 'w'
      return size[1] if dimension == 'h'
      return size unless dimension
    rescue FastImage::ImageFetchFailure => e
      raise "Unable to fetch image size for: #{source}. Error: #{e.message}"
    rescue => e
      raise "An error occurred while fetching image size for: #{source}. Error: #{e.message}"
    end
  end
end

Liquid::Template.register_filter(ImageSizeFilter)
