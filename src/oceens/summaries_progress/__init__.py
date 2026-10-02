"""Progression d'un sondage dans la file des synthèses.

Une seule question : `progress(session, survey_id)` répond combien de synthèses
sont faites, combien il y en a, combien ont échoué, et combien de temps il reste.
La file est la table `summaries` ; le sens de `http_status` reste dans ce paquet.
"""

from oceens.summaries_progress._queue import Progress, progress

__all__ = ["Progress", "progress"]
