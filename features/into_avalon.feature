
Feature: Energizing Avalon with Reveries

    Scenario: Launch <DCC_App> with Reveries pipeline implemented
        Given an environment that meets the Avalon's demand
        When I initiate Avalon
        And I create a project <PROJECT_NAME>
        And I set my task: <SILO> - <ASSET> - <TASK>
        And I launch <DCC_App>
        Then <DCC_App> will be startup with Reveries pipeline

        Examples:
        	|  DCC_App  |  PROJECT_NAME |  SILO  | ASSET | TASK  |
        	|   mayapy  | AdventureTime | assets | Dummy | model |
