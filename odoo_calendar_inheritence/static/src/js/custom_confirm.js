//odoo.define('odoo_calendar_inheritence.custom_confirm', function (require) {
//    'use strict';
//
//    var core = require('web.core');
//    var Dialog = require('web.Dialog');
//    var FormViewDialog = require('web.FormViewDialog');
//    var _t = core._t;
//
//    FormViewDialog.include({
//        events: _.extend({}, FormViewDialog.prototype.events, {
//            'click .o_button_delete': '_onDeleteClick',
//        }),
//
//        _onDeleteClick: function (event) {
//            event.preventDefault();
//            var self = this;
//
//            new Dialog(this, {
//                title: _t('Delete Record'),
//                size: 'medium',
//                buttons: [
//                    {
//                        text: _t('Delete'),
//                        classes: 'btn-primary',
//                        click: function () {
//                            self._rpc({
//                                model: self.model,
//                                method: 'unlink',
//                                args: [[self.res_id]],
//                            }).then(function () {
//                                self.trigger_up('record_delete');
//                                self.destroy();
//                            });
//                        },
//                    },
//                    {
//                        text: _t('Cancel'),
//                        close: true,
//                    },
//                ],
//                $content: $('<div>').html('<p>If you delete this meeting, all meeting data will be permanently lost including action points, documents, and board park.</p>'),
//            }).open();
//        },
//    });
//
//    return FormViewDialog;
//});
