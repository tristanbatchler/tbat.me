require 'fastimage'

module ImageSizeFilter
  def image_size(source, dimension = nil)
    source = File.join(Dir.pwd, source.sub(/^\//, ''))

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
