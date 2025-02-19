from functools import partial
from os import path
from time import sleep

import pytest
from testpath import MockCommand

config_file_path = f"{path.dirname(path.realpath(__file__))}/projects/"


@pytest.fixture
def internal_ip(mocker):
    return lambda page, interface, ip: mocker.patch(
        f"pt_miniscreen.pages.network.{page}.get_internal_ip",
        lambda iface: ip if interface == iface else "No IP address",
    )


@pytest.fixture
def go_to_projects_page(miniscreen):
    def go():
        # enter projects menu
        miniscreen.down_button.release()
        sleep(1)
        miniscreen.down_button.release()
        sleep(1)
        miniscreen.down_button.release()
        sleep(1)
        miniscreen.select_button.release()
        sleep(1)

    return go


@pytest.fixture
def create_project(mocker):
    def create_project_rows(project_number):
        from pt_miniscreen.pages.root.projects import ProjectConfig, ProjectRow

        pages = []
        for project in range(project_number):
            config = ProjectConfig(
                file=f"/tmp/config-{project + 1}.cfg",
                title=f"Project #{project + 1}",
                start="my-custom-start-command",
                image="",
                exit_condition="",
            )
            pages.append(partial(ProjectRow, config))
        return pages

    def mock_project_rows(projects_to_create):
        mocker.patch(
            "pt_miniscreen.pages.root.projects.ProjectList.load_project_rows",
            side_effect=lambda: create_project_rows(projects_to_create),
        )
        mocker.patch(
            "pt_miniscreen.pages.root.projects.ProjectDirectoryList.directory_has_projects",
            return_value=True,
        )
        mocker.patch(
            "pt_miniscreen.pages.root.projects.switch_user",
            return_value=None,
        )

    return mock_project_rows


def test_no_user_projects_available(miniscreen, go_to_projects_page, snapshot, mocker):
    go_to_projects_page()
    snapshot.assert_match(miniscreen.device.display_image, "only-package-projects.png")


def test_open_projects_menu(miniscreen, go_to_projects_page, snapshot, create_project):
    create_project(1)
    go_to_projects_page()
    snapshot.assert_match(
        miniscreen.device.display_image, "projects-page-subsections.png"
    )


def test_open_user_projects(miniscreen, go_to_projects_page, snapshot, create_project):
    create_project(1)
    go_to_projects_page()

    # access user projects
    miniscreen.select_button.release()
    sleep(1)
    snapshot.assert_match(miniscreen.device.display_image, "1-project-row.png")

    # access project page
    miniscreen.select_button.release()
    sleep(1)
    snapshot.assert_match(miniscreen.device.display_image, "project-page.png")


def test_opening_project_page_runs_project(
    miniscreen, go_to_projects_page, snapshot, create_project, mocker
):
    mocker.patch(
        "pt_miniscreen.pages.root.projects.get_user_using_first_display",
        return_value=None,
    )
    create_project(1)
    go_to_projects_page()

    # access user projects
    miniscreen.select_button.release()
    sleep(1)
    snapshot.assert_match(miniscreen.device.display_image, "1-project-row.png")

    with MockCommand("my-custom-start-command") as start_command:
        # access project page
        miniscreen.select_button.release()
        sleep(1)
        snapshot.assert_match(miniscreen.device.display_image, "project-page.png")
        # wait for the project process to finish
        sleep(4)

    assert len(start_command.get_calls()) == 1


def test_returns_to_project_list_when_project_process_finishes(
    miniscreen, go_to_projects_page, snapshot, create_project
):
    create_project(1)
    go_to_projects_page()

    # access user projects
    miniscreen.select_button.release()
    sleep(1)
    snapshot.assert_match(miniscreen.device.display_image, "1-project-row.png")

    with MockCommand("my-custom-start-command"):
        # access project page
        miniscreen.select_button.release()
        sleep(1)
        snapshot.assert_match(miniscreen.device.display_image, "project-page.png")
        # wait for the project process to finish
        sleep(4)

    snapshot.assert_match(miniscreen.device.display_image, "1-project-row.png")


def test_returns_to_project_list_when_project_process_errors(
    miniscreen, go_to_projects_page, snapshot, create_project
):
    create_project(1)
    go_to_projects_page()

    # access user projects
    miniscreen.select_button.release()
    sleep(1)
    snapshot.assert_match(miniscreen.device.display_image, "1-project-row.png")

    # don't mock 'my-custom-start-command'

    # access project page
    miniscreen.select_button.release()
    sleep(1)
    snapshot.assert_match(miniscreen.device.display_image, "project-page.png")
    # wait for the project process to finish
    sleep(4)

    snapshot.assert_match(miniscreen.device.display_image, "1-project-row.png")


def test_first_item_is_selected_by_default(
    miniscreen, go_to_projects_page, snapshot, create_project
):
    create_project(3)
    go_to_projects_page()
    snapshot.assert_match(
        miniscreen.device.display_image, "first-project-is-selected.png"
    )


def test_load_project_config_from_valid_file():
    from pt_miniscreen.pages.root.projects import ProjectConfig

    config = ProjectConfig.from_file(f"{config_file_path}/valid/valid_project.cfg")
    assert config.title == "my project"
    assert config.start == "python3 project.py"
    assert config.exit_condition == "?"


def test_load_project_config_raises_on_invalid_file():
    from pt_miniscreen.pages.root.projects import InvalidConfigFile, ProjectConfig

    with pytest.raises(InvalidConfigFile):
        ProjectConfig.from_file(f"{config_file_path}/invalid/invalid_project.cfg")


def test_project_list_loads_projects_from_directories(mocker, create_component):
    mocker.patch(
        "pt_miniscreen.pages.root.projects.ProjectDirectoryList.PROJECT_DIRECTORY_LOOKUP",
        {"Test projects": f"{config_file_path}"},
    )
    from pt_miniscreen.pages.root.projects import ProjectDirectoryList

    project_list = create_component(ProjectDirectoryList)
    assert len(project_list.rows) == 1
    selected_row = project_list.selected_row
    assert selected_row.page is not None


def test_project_list_doesnt_add_project_page_when_projects_not_found(
    mocker, create_component
):
    from pt_miniscreen.pages.root.projects import ProjectList

    project_list = create_component(ProjectList, directory="")
    assert len(project_list.rows) == 1
    selected_row = project_list.selected_row
    assert selected_row.page is None
