"""Muses — instance-side seam to the suddenly-muses hub (muse.suddenly.social).

This app is a *client boundary* only. It holds no editorial pipeline: the
tables, best-of-N pipeline and pattern matching live in the separate
``suddenly-muses`` service. Everything here is orchestration on the instance
side (#76 MusesClient), and every caller degrades cleanly when the hub is
disabled or unreachable (#88 mode dégradé).
"""
