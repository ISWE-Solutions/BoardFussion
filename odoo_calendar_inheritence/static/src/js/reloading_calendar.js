/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { useService } from "@web/core/utils/hooks";
import { ListRenderer } from "@web/views/list/list_renderer";

// Patch FormController for menu reloading (existing code)
patch(FormController.prototype, {
    __patch__: "reloading_calendar",
    setup() {
        super.setup();
        this.menuService = useService("menu");
    },
    async saveRecord() {
        const result = await super.saveRecord(...arguments);
        if (this.model.root.resModel === "calendar.event") {
            this.menuService.reload();
        }
        return result;
    },
});

patch(ListRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this.props.canCreate = false;
    },
    async _render() {
        await super._render(...arguments);
        // Hide any button with text "Add Agenda"
        const buttons = document.querySelectorAll('button:contains("Add Agenda")');
        buttons.forEach(button => button.style.display = 'none');
    },
});