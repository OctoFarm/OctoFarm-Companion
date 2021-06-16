/*
 * View model for OctoFarm-Companion
 *
 * Author: David Zwart
 * License: AGPLv3
 */
$(function() {
    function OctofarmCompanionViewModel(parameters) {
        var self = this;

        // assign the injected parameters, e.g.:
        self.loginStateViewModel = parameters[0];
        self.settingsViewModel = parameters[1];

        // TODO: Implement your plugin's view model here.

        // this will hold the URL currently displayed by the iframe
        self.currentUrl = ko.observable();

        // this will hold the URL entered in the text field
        self.newUrl = ko.observable();
    }

    /* view model class, parameters for constructor, container to bind to
     * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
     * and a full list of the available options.
     */
    OCTOPRINT_VIEWMODELS.push({
        construct: OctofarmCompanionViewModel,
        // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
        dependencies: [
            "loginStateViewModel", "settingsViewModel"
        ],
        // Elements to bind to, e.g. #settings_plugin_octofarm_companion, #tab_plugin_octofarm_companion, ...
        elements: [ /* ... */ ]
    });
});
