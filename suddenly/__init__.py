# Suddenly - Federated Fiction Network

# Single source of truth for the software version (BookWyrm/Mastodon pattern:
# a committed constant, read at runtime — never derived from git tags or package
# metadata). Feeds both the UI footer and NodeInfo `software.version`, so the
# federation can list instances with their version. Bumped once per release by
# the maintainer; volunteers deploying the project never manage it by hand.
__version__ = "0.8.0"
