/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";  // Import FormController from @web
import { useService } from "@web/core/utils/hooks";  // Hook for services (e.g., action service)

export default class CalendarEventRestriction extends FormController {
    constructor(parent, model, res_id) {
        super(parent, model, res_id);  // Inherit from FormController
        this.actionService = useService("action");  // Use the action service
    }

    // Override the _renderStatButton method to control button visibility
    _renderStatButton(button, $button) {
        console.log("Rendering button:", button);  // Log the button for debugging

        super._renderStatButton(button, $button);  // Ensure base functionality is preserved

        // Check for the specific button to hide (e.g., action_open_documents)
        if (button.name === "action_open_documents") {  // Use button.name directly
            console.log("Found 'action_open_documents' button");

            // Fetch the current record data
            const record = this.model.get(this.handle, { raw: true });
            console.log("Record data:", record);  // Log the record data to verify

            // Check if the current user is in the restricted list
            if (record && record.data && record.data.is_user_restricted) {
                console.log("User is restricted, hiding the button");
                $button.hide();  // Hide the button if the user is restricted
            } else {
                console.log("User is not restricted, button will remain visible");
            }
        }
    }
}
