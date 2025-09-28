"""NiceGUI frontend for the Running Coach application."""

from typing import Any, Dict, Optional

from fastapi import FastAPI

from app.constants import (
    UI_TITLE,
    UI_SUBTITLE,
    UI_GOAL_LABEL,
    UI_TIME_LABEL,
    UI_SUBMIT_BUTTON,
    UI_HISTORY_TAB,
    UI_PROGRAM_TAB,
    UI_LOADING_MESSAGE,
    UI_SUCCESS_MESSAGE,
    UI_ERROR_MESSAGE,
    UI_HISTORY_EMPTY,
    UI_HISTORY_ERROR,
    MIN_GOAL_KM,
    MAX_GOAL_KM,
    MIN_TIME_WEEKS,
    MAX_TIME_WEEKS,
    DEFAULT_GOAL_KM,
    DEFAULT_TIME_WEEKS
)
from app.utils.http_client import api_client
from app.utils.logger import logger

from nicegui import ui


class RunningCoachUI:
    """Main UI class for the Running Coach application."""

    def __init__(self):
        self.goal_input: Optional[ui.number] = None
        self.time_input: Optional[ui.number] = None
        self.submit_button: Optional[ui.button] = None
        self.loading_spinner: Optional[ui.spinner] = None
        self.result_container: Optional[ui.column] = None
        self.history_container: Optional[ui.column] = None
        self.save_locally_toggle: Optional[ui.checkbox] = None
        self.last_program: Optional[Dict[str, Any]] = None

    def create_form(self) -> None:
        """Create the main form for program generation."""
        with ui.column().classes('w-full max-w-md mx-auto gap-4'):
            ui.label(UI_TITLE).classes('text-2xl font-bold text-center')
            ui.label(UI_SUBTITLE).classes('text-center text-gray-600 mb-6')

            # Goal input
            ui.label(UI_GOAL_LABEL).classes('text-sm font-medium')
            self.goal_input = ui.number(
                value=DEFAULT_GOAL_KM,
                min=MIN_GOAL_KM,
                max=MAX_GOAL_KM,
                step=0.1,
                precision=1
            ).classes('w-full')

            # Time input
            ui.label(UI_TIME_LABEL).classes('text-sm font-medium')
            self.time_input = ui.number(
                value=DEFAULT_TIME_WEEKS,
                min=MIN_TIME_WEEKS,
                max=MAX_TIME_WEEKS,
                step=1,
                precision=0
            ).classes('w-full')

            # Save locally toggle
            self.save_locally_toggle = ui.checkbox('Save locally').classes('text-sm')

            # Submit button
            self.submit_button = ui.button(
                UI_SUBMIT_BUTTON,
                on_click=self._handle_submit
            ).classes('w-full bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded')

            # Loading spinner
            self.loading_spinner = ui.spinner(size='lg').classes('hidden')

            # Result container
            self.result_container = ui.column().classes('w-full mt-6')

    def create_history_tab(self) -> None:
        """Create the history tab content."""
        self.history_container = ui.column().classes('w-full gap-4')
        self._load_history()

    async def _handle_submit(self) -> None:
        """Handle form submission."""
        if not self.goal_input or not self.time_input:
            logger.error("Form inputs not initialized")
            return

        goal_km = self.goal_input.value
        time_weeks = int(self.time_input.value)

        # Validate inputs
        if not goal_km or not time_weeks:
            ui.notify("Please fill in all fields", type='warning')
            return

        if goal_km < MIN_GOAL_KM or goal_km > MAX_GOAL_KM:
            ui.notify(f"Goal must be between {MIN_GOAL_KM} and {MAX_GOAL_KM} km", type='warning')
            return

        if time_weeks < MIN_TIME_WEEKS or time_weeks > MAX_TIME_WEEKS:
            ui.notify(f"Time must be between {MIN_TIME_WEEKS} and {MAX_TIME_WEEKS} weeks", type='warning')
            return

        # Show loading state
        self._show_loading()

        try:
            logger.info("Submitting program request", goal_km=goal_km, time_weeks=time_weeks)

            # Call API
            result = await api_client.create_program(goal_km, time_weeks)

            logger.info("Program generated successfully", program_id=result.get('program_id'))

            # Store last program for local saving
            self.last_program = result

            # Show success state
            self._show_result(result)

            # Save locally if enabled
            if self.save_locally_toggle and self.save_locally_toggle.value:
                self._save_locally(result)

            ui.notify(UI_SUCCESS_MESSAGE, type='positive')

        except Exception as e:
            logger.error("Failed to generate program", error=str(e))
            self._show_error(str(e))
            ui.notify(UI_ERROR_MESSAGE, type='negative')

        finally:
            self._hide_loading()

    def _show_loading(self) -> None:
        """Show loading state."""
        if self.submit_button:
            self.submit_button.props('loading')
            self.submit_button.disable()

        if self.loading_spinner:
            self.loading_spinner.classes(remove='hidden')

        if self.result_container:
            self.result_container.clear()
            with self.result_container:
                ui.label(UI_LOADING_MESSAGE).classes('text-center text-gray-600')

    def _hide_loading(self) -> None:
        """Hide loading state."""
        if self.submit_button:
            self.submit_button.props(remove='loading')
            self.submit_button.enable()

        if self.loading_spinner:
            self.loading_spinner.classes('hidden')

    def _show_result(self, result: Dict[str, Any]) -> None:
        """Show the generated program result."""
        if not self.result_container:
            return

        self.result_container.clear()

        with self.result_container:
            # Program info
            ui.label(f"Program ID: {result.get('program_id', 'N/A')}").classes('text-sm text-gray-500')
            ui.label(f"Goal: {result.get('goal_km', 'N/A')} km in {result.get('time_weeks', 'N/A')} weeks").classes('text-lg font-semibold')

            # Weekly plans
            ui.label("Weekly Training Plan").classes('text-lg font-semibold mt-4')
            weekly_plans = result.get('weekly_plans', [])

            if weekly_plans:
                with ui.column().classes('gap-2'):
                    for plan in weekly_plans:
                        with ui.card().classes('p-4'):
                            ui.label(f"Week {plan.get('week_number', 'N/A')}").classes('font-semibold')
                            ui.label(f"Total Distance: {plan.get('total_distance_km', 'N/A')} km")
                            ui.label(f"Runs per Week: {plan.get('runs_per_week', 'N/A')}")
                            ui.label(f"Long Run: {plan.get('long_run_km', 'N/A')} km")
                            if plan.get('notes'):
                                ui.label(f"Notes: {plan.get('notes')}").classes('text-sm text-gray-600')
            else:
                ui.label("No weekly plans available").classes('text-gray-500')

            # Recommendations
            recommendations = result.get('recommendations', [])
            if recommendations:
                ui.label("Recommendations").classes('text-lg font-semibold mt-4')
                with ui.column().classes('gap-2'):
                    for rec in recommendations:
                        with ui.card().classes('p-4'):
                            ui.label(f"{rec.get('title', 'N/A')}").classes('font-semibold')
                            ui.label(f"Category: {rec.get('category', 'N/A')}").classes('text-sm text-gray-600')
                            ui.label(f"Priority: {rec.get('priority', 'N/A')}").classes('text-sm text-gray-600')
                            if rec.get('description'):
                                ui.label(rec.get('description')).classes('text-sm')
            else:
                ui.label("No recommendations available").classes('text-gray-500')

    def _show_error(self, error_message: str) -> None:
        """Show error state."""
        if not self.result_container:
            return

        self.result_container.clear()

        with self.result_container:
            with ui.card().classes('p-4 bg-red-50 border-red-200'):
                ui.label("Error").classes('font-semibold text-red-800')
                ui.label(error_message).classes('text-red-700')

    async def _load_history(self) -> None:
        """Load and display program history."""
        if not self.history_container:
            return

        self.history_container.clear()

        with self.history_container:
            ui.label("Loading history...").classes('text-center text-gray-600')

        try:
            logger.info("Loading program history")

            result = await api_client.get_history()
            programs = result.get('programs', [])

            self.history_container.clear()

            with self.history_container:
                if not programs:
                    ui.label(UI_HISTORY_EMPTY).classes('text-center text-gray-600')
                    return

                ui.label(f"Program History ({len(programs)} programs)").classes('text-lg font-semibold mb-4')

                for program in programs:
                    with ui.card().classes('p-4 mb-4'):
                        ui.label(f"Program ID: {program.get('program_id', 'N/A')}").classes('font-semibold')
                        ui.label(f"Goal: {program.get('goal_km', 'N/A')} km in {program.get('time_weeks', 'N/A')} weeks")
                        ui.label(f"Created: {program.get('created_at', 'N/A')}").classes('text-sm text-gray-600')

                        # Show preview of first week plan
                        weekly_plans = program.get('weekly_plans', [])
                        if weekly_plans:
                            first_week = weekly_plans[0]
                            ui.label(f"First Week: {first_week.get('total_distance_km', 'N/A')} km total").classes('text-sm text-gray-600')

        except Exception as e:
            logger.error("Failed to load history", error=str(e))
            self.history_container.clear()

            with self.history_container:
                ui.label(UI_HISTORY_ERROR).classes('text-center text-red-600')

    def _save_locally(self, program: Dict[str, Any]) -> None:
        """Save program to browser localStorage (TODO: implement if needed)."""
        # TODO: Implement localStorage saving if NiceGUI supports it
        # For now, just log the action
        logger.info("Local save requested", program_id=program.get('program_id'))

    def create_ui(self) -> None:
        """Create the complete UI."""
        with ui.tabs().classes('w-full') as tabs:
            program_tab = ui.tab(UI_PROGRAM_TAB)
            history_tab = ui.tab(UI_HISTORY_TAB)

        with ui.tab_panels(tabs, value=program_tab).classes('w-full'):
            with ui.tab_panel(program_tab):
                self.create_form()

            with ui.tab_panel(history_tab):
                self.create_history_tab()


def mount_ui(app: FastAPI) -> None:
    """Mount the NiceGUI UI to the FastAPI app."""
    logger.info("Mounting NiceGUI UI to FastAPI app")

    # Create UI instance
    ui_instance = RunningCoachUI()
    ui_instance.create_ui()

    # Mount NiceGUI to FastAPI on a specific path to avoid conflicts
    ui.run_with(
        app,
        title=UI_TITLE,
        favicon='🏃‍♂️',
        mount_path='/ui'
    )

    logger.info("NiceGUI UI mounted successfully at /ui")
