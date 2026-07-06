#!/usr/bin/env perl
use strict;
use warnings;

my $file = shift @ARGV;
die "Usage: $0 <theory-file>\n" unless defined $file;

open my $fh, '<', $file or die "Cannot read $file: $!\n";
local $/;
my $text = <$fh>;

my $last_export;
my @command;
my $collecting = 0;

for my $line (split /\n/, $text) {
  if ($line =~ /^\s*export_code\b/) {
    @command = ($line);
    $collecting = 1;
  } elsif ($collecting) {
    push @command, $line;
  }

  if ($collecting && $line =~ /\bin\s+Rust\b/) {
    my $command_text = join ' ', @command;
    if ($command_text =~ /^\s*export_code\s+(.*?)\s+in\s+Rust\b/s) {
      $last_export = $1;
    }
    @command = ();
    $collecting = 0;
  }
}

if (!defined $last_export) {
  print "0\n";
  exit 0;
}

$last_export =~ s/^\s+|\s+$//g;
my @items = grep { length $_ } split /\s+/, $last_export;
print scalar(@items), "\n";
