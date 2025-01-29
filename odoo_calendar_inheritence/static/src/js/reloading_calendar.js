///** @odoo-module **/
//
//import { patch } from "@web/core/utils/patch";
//import { FormController } from "@web/views/form/form_controller";
//import { useService } from "@web/core/utils/hooks";
//import { ListRenderer } from "@web/views/list/list_renderer";
//import { ListController } from "@web/views/list/list_controller";
//import { data } from "@web/core";
//
//var CustomListController = ListController.extend({
//    renderButtons: function ($node) {
//        this._super($node);
//        this.$buttons.find('.o_list_button_add').hide();
//    },
//});
//
//data.modelFieldsviewController.include({
//    _getView: function () {
//        var res = this._super.apply(this, arguments);
//        if (this.model === 'calendar.event.product.line') {
//            res.controller = CustomListController;
//        }
//        return res;
//    },
//});