/** @odoo-module **/
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import {UserMenu} from "@web/webclient/user_menu/user_menu";
import { Component } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
patch(UserMenu.prototype, {
    setup() {
       super.setup();
       console.log("UserMenu setup");
    },
    
});
