https://tbat.me

A personal home page and small blog built with Jekyll.

## Quickstart for Arch Linux
```bash
git clone https://github.com/tristanbatchler/tbat.me
sudo pacman -S make gcc ruby rubygems
echo -e "# Add ruby gem apps to path \nexport PATH=\"\$PATH:\$(ruby -e 'print Gem.user_dir')/bin"\" >> ~/.profile
source ~/.profile
gem install jekyll bundler rouge
cd tbat.me
bundle install
bundle exec jekyll serve &
xdg-open http://localhost:4000 &
```

[![Netlify Status](https://api.netlify.com/api/v1/badges/0b21337d-5f89-4321-bd90-27c7ef709574/deploy-status)](https://app.netlify.com/sites/tbatch/deploys)
