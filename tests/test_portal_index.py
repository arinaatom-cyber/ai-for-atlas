from atlas_agent.viz.portal_index import (
    atlas_organ_map_url,
    build_organ_index,
    format_finding_note,
    project_github_links,
    repository_url,
)


def test_repository_url_pxd():
    assert "PXD012173" in repository_url("PXD012173")
    assert repository_url("PDC000110").startswith("https://proteomic")


def test_repository_url_massive_iprox():
    msv = repository_url("MSV000080000")
    assert "massive.ucsd.edu" in msv
    assert "accession=MSV000080000" in msv
    ipx = repository_url("IPX0001234000")
    assert ipx
    assert "iprox" in ipx.lower()
    assert "IPX0001234000" in ipx


def test_resolve_publication_links_offline():
    from atlas_agent.viz.portal_index import article_description, resolve_publication_links

    item = {
        "accession": "PXD012345",
        "title": "Human TMT liver proteome PMID 38765432",
        "description": "Paired tumor and adjacent liver tissue, TMT11.",
    }
    resolve_publication_links(item, fetch_pride_pmid=False)
    assert item["pmid"] == "38765432"
    assert "38765432" in item["pubmed_url"]
    assert "pride" in item["repository_url"]
    assert "PXD012345" in item["repository_url"]
    assert "Paired tumor" in item["article_description"]
    assert "Paired tumor" in article_description(item)


def test_atlas_organ_map_url():
    assert "?organ=Bladder" in atlas_organ_map_url("Bladder")


def test_github_folder_links():
    cfg = {
        "github": {
            "atlas_repo": "https://github.com/arinaatom-cyber/TMT",
            "data_repo": "https://github.com/arinaatom-cyber/tmt-projects",
            "raw_branch": "main",
            "atlas_projects_path": "projects",
            "data_projects_path": "Projects",
        }
    }
    links = project_github_links(cfg, "PXD029216")
    assert "tmt-projects" in links["tmt_projects_folder"]
    assert "PXD029216" in links["tmt_projects_folder"]


def test_format_finding_note_keywords():
    note = format_finding_note(
        {"accession": "PXD099999", "source": "pride", "similar_in_catalog": [{"project_id": "PXD012173", "score": 0.8}]},
        keywords=["TMT", "colon"],
    )
    assert "Keywords from title" in note
    assert "PXD012173" in note
