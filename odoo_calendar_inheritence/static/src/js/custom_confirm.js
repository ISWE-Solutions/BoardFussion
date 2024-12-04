/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { jsonrpc } from "@web/core/network/rpc_service";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export default class MyCustomModule {
    constructor(parent, model, res_id) {
        this.actionService = useService("action");
        this.model = model;
        this.res_id = res_id;
    }

    // Bind the delete button event
    start() {
        const deleteButton = document.querySelector('.o_button_delete');
        if (deleteButton) {
            deleteButton.addEventListener('click', this._onDeleteClick.bind(this));
        }
    }

    _onDeleteClick(event) {
        event.preventDefault();
        const self = this;

        const confirmationDialog = new Dialog(this, {
            title: _t('Delete Record'),
            size: 'medium',
            buttons: [
                {
                    text: _t('Delete'),
                    classes: 'btn-primary',
                    close: true,
                    click: function () {
                        jsonrpc({
                            model: self.model,
                            method: 'unlink',
                            args: [[self.res_id]],
                        }).then(() => {
                            self.actionService.doAction({
                                name: _t('Record Deleted'),
                                type: 'ir.actions.act_window_close',
                            });
                        });
                    },
                },
                {
                    text: _t('Cancel'),
                    close: true,
                },
            ],
            $content: $('<div>').html('<p>If you delete this meeting, all meeting data will be permanently lost including action points, documents, and board park.</p>'),
        });

        confirmationDialog.open();
    }
}
