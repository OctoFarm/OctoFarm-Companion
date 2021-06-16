/*
 * View model for OctoFarm-Companion
 *
 * Author: David Zwart
 * License: AGPLv3
 */
$(function () {
    function OctofarmCompanionViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settings = parameters[1];

        self.testUrlBackend = function (url) {

            var url = PLUGIN_BASEURL + "octofarm_companion/test/" + url;

            var payload = {
                command: "read",
                until: until
            };

            $.ajax({
                url: url,
                type: "POST",
                dataType: "json",
                data: JSON.stringify(payload),
                contentType: "application/json; charset=UTF-8",
                success: function () {
                    // if (reload) {
                    //     self.retrieveData();
                    // }
                }
            });
        };
    }

    /* view model class, parameters for constructor, container to bind to
     * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
     * and a full list of the available options.
     */
    OCTOPRINT_VIEWMODELS.push([
        OctofarmCompanionViewModel,
        // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
        [
            "loginStateViewModel", "settingsViewModel"
        ],
        // Elements to bind to, e.g. #settings_plugin_octofarm_companion, #tab_plugin_octofarm_companion, ...
        [
            
            // "#settings_plugin_octofarm_companion",
            // "#navbar_plugin_octofarm_companion"
        ]
    ]);
});
