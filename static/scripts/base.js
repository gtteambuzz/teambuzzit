'use strict';

$(function () {
    $('input[autofocus]').each(function (i, element) {
        var $this = $(this);
        $this.val($this.val());
    });

    $('[data-filters]').each(function () {
        var $form = $(this);
        var model = $form.data('filters');
        var $models = $('[data-model="' + model + '"]');
        var $inputs = $form.find('input, select');
        var $notice = $('[data-model-filter-notice="' + model + '"]');

        $form.on('input', function () {

            var params = {};
            $inputs.each(function () {
                var $input = $(this);
                params[$input.attr('name')] = $input.val();
            });

            var total = 0;
            var shown = 0;
            $models.each(function () {
                var shouldShow = true;
                var $model = $(this);
                for (name in params) {
                    var value = params[name].toLowerCase();
                    var body = $model.find('[data-name="' + name + '"]').text().toLowerCase();
                    if (!body) {
                        body = $model.data(name) || '';
                    }
                    shouldShow = shouldShow && (!value || body.indexOf(value) >= 0);
                }
                if (shouldShow) shown++;
                total++;
                $model[shouldShow ? 'removeClass' : 'addClass']('hidden');
            });

            var noticeText = total === shown && total > 0 ? '' : 'Showing ' + shown + ' of ' + total + ' ' + model + 's';
            $notice.text(noticeText);
            $notice[noticeText ? 'removeClass' : 'addClass']('hidden');
        });

        $form.find('button[type=reset]').on('click', function () {
            $inputs.each(function () {
                var $input = $(this);
                var defaultInput = $input.find('[default]');
                var defaultValue = defaultInput ? defaultInput.val() : "";
                $input.val(defaultValue);
            });
            $inputs.trigger('input');
        });

        $form.trigger('input');
    });
});
