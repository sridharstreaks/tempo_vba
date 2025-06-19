#!/usr/bin/env bash

file="your.xml"
max=5                   # number of get1,get2,... blocks
search="YOUR_SEARCH"    # the word you’re looking for

for (( i=1; i<=max; i++ )); do
  id="get${i}"
  awk -v ID="$id" -v W="$search" '
    # When we see the opening tag with the right id, turn on in_block
    $0 ~ "<util:list[[:space:]]+id=\"" ID "\"[[:space:]]+class=\"list\">" {
      in_block=1
      next
    }
    # When we see the closing tag while in_block, turn it off
    in_block && $0 ~ "</util:list>" {
      in_block=0
      next
    }
    # If we're in the right block, look for your word
    in_block && index($0, W) {
      print "✔ Found \"" W "\" in block " ID
      found=1
      # you could `exit` here if you only want the first hit
    }
    # At end of file, if we never found it, print a not-found message
    END {
      if (!found) print "✘ No \"" W "\" in block " ID
    }
  ' "$file"
done
