#
# Copyright (c) 2021, Neptune Labs Sp. z o.o.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
__all__ = [
    'NeptuneCallback',
    'log_study_metadata',
    'load_study_from_run',
]


from typing import Iterable, Union, List, Optional

import contextlib
import optuna

from neptune_optuna import __version__

try:
    # neptune-client=0.9.0+ package structure
    import neptune.new as neptune
    from neptune.new.types import File
    from neptune.new.internal.utils import verify_type
    from neptune.new.internal.utils.compatibility import expect_not_an_experiment
except ImportError:
    # neptune-client>=1.0.0 package structure
    import neptune
    from neptune.types import File
    from neptune.internal.utils import verify_type
    from neptune.internal.utils.compatibility import expect_not_an_experiment

INTEGRATION_VERSION_KEY = 'source_code/integrations/neptune-optuna'

class NeptuneCallback:
    """A callback that logs the metadata from Optuna Study to Neptune.

    With this callback, you can log and display:

    * values and params for each trial
    * current best values and params for the study
    * visualizations from the `optuna.visualizations` module
    * parameter distributions for each trial
    * study object itself to load it later
    * and more

    Args:
        run(neptune.Run): Neptune Run.
        base_namespace(str, optional): Namespace inside the Run where your study metadata is logged. Defaults to ''.
        target_names(List[str], optional): Names of the study objectives to log (i.e., "Accuracy"). Defaults to None.
        plots_update_freq(int, str, optional): Frequency at which plots are logged and updated in Neptune.
            If you pass integer value k, plots will be updated every k iterations.
            If you pass the string 'never', plots will not be logged. Defaults to 1.
        study_update_freq(int, str, optional): It is a frequency at which a study object is logged and updated in Neptune.
            If you pass integer value k, the study will be updated every k iterations.
            If you pass the string 'never', plots will not be logged. Defaults to 1.
        visualization_backend(str, optional): Which visualization backend is used for 'optuna.visualizations' plots.
            It can be one of 'matplotlib' or 'plotly'. Defaults to 'plotly'.
        log_plot_contour(bool, optional): If 'True' the `optuna.visualizations.plot_contour`
            visualization will be logged to Neptune. Defaults to `True`.
        log_plot_edf(bool, optional): If 'True' the `optuna.visualizations.plot_edf`
            visualization will be logged to Neptune. Defaults to `True`.
        log_plot_parallel_coordinate(bool, optional): If 'True' the `optuna.visualizations.plot_parallel_coordinate`
            visualization will be logged to Neptune. Defaults to `True`.
        log_plot_param_importances(bool, optional): If 'True' the `optuna.visualizations.plot_param_importances`
            visualization will be logged to Neptune. Defaults to `True`.
        log_plot_pareto_front(bool, optional): If 'True' the `optuna.visualizations.plot_pareto_front`
            visualization will be logged to Neptune.
            If your `optuna.study` is not multi-objective this plot is not logged. Defaults to `True`.
        log_plot_slice(bool, optional): If 'True' the `optuna.visualizations.plot_slice`
            visualization will be logged to Neptune. Defaults to `True`.
        log_plot_intermediate_values(bool, optional): If 'True' the `optuna.visualizations.plot_intermediate_values`
            visualization will be logged to Neptune.
            If your `optuna.study` is not using pruners this plot is not logged. Defaults to `True`. Defaults to `True`.
        log_plot_optimization_history(bool, optional): If 'True' the `optuna.visualizations.plot_optimization_history`
            visualization will be logged to Neptune. Defaults to `True`.

    Examples:
        Create a Run:
        >>> import neptune.new as neptune
        ... run = neptune.init('my_workspace/my_project')

        Initialize a NeptuneCallback:
        >>> import neptune.new.integrations.optuna as optuna_utils
        ... neptune_callback = optuna_utils.NeptuneCallback(run)

        Or `optionally` pass a list of objective names:
            Single objective:
            ... neptune_callback = optuna_utils.NeptuneCallback(run, target_names=['accuracy'])
            Multi-objective:
            ... neptune_callback = optuna_utils.NeptuneCallback(run, target_names=['FLOPS', 'accuracy'])

        Log single and multi-objective Study metadata to Neptune by passing NeptuneCallback to the Optuna Study:
        >>> study = optuna.create_study(direction='maximize')
        ... study.optimize(objective, n_trials=5, callbacks=[neptune_callback])


    For more information, see `Neptune-Optuna integration docs page`_.
    .. _Neptune Optuna integration docs page:
       https://docs.neptune.ai/integrations-and-supported-tools/hyperparameter-optimization/optuna
    """

    def __init__(self,
                 run: neptune.Run,
                 base_namespace: str = '',
                 target_names: List[str] = None,
                 plots_update_freq: Union[int, str] = 1,
                 study_update_freq: Union[int, str] = 1,
                 visualization_backend: str = 'plotly',
                 log_plot_contour: bool = True,
                 log_plot_edf: bool = True,
                 log_plot_parallel_coordinate: bool = True,
                 log_plot_param_importances: bool = True,
                 log_plot_pareto_front: bool = True,
                 log_plot_slice: bool = True,
                 log_plot_intermediate_values: bool = True,
                 log_plot_optimization_history: bool = True):

        expect_not_an_experiment(run)
        verify_type('run', run, neptune.Run)
        verify_type('base_namespace', base_namespace, str)
        verify_type('target_names', target_names, (List[str], type(None)))
        verify_type('log_plots_freq', plots_update_freq, (int, str, type(None)))
        verify_type('log_study_freq', study_update_freq, (int, str, type(None)))
        verify_type('visualization_backend', visualization_backend, (str, type(None)))
        verify_type('log_plot_contour', log_plot_contour, (bool, type(None)))
        verify_type('log_plot_edf', log_plot_edf, (bool, type(None)))
        verify_type('log_plot_parallel_coordinate', log_plot_parallel_coordinate, (bool, type(None)))
        verify_type('log_plot_param_importances', log_plot_param_importances, (bool, type(None)))
        verify_type('log_plot_pareto_front', log_plot_pareto_front, (bool, type(None)))
        verify_type('log_plot_slice', log_plot_slice, (bool, type(None)))
        verify_type('log_plot_intermediate_values', log_plot_intermediate_values, (bool, type(None)))
        verify_type('log_plot_optimization_history', log_plot_optimization_history, (bool, type(None)))

        self.run = run[base_namespace]
        self._target_names = target_names
        self._namespaces = ''
        self._visualization_backend = visualization_backend
        self._plots_update_freq = plots_update_freq
        self._study_update_freq = study_update_freq
        self._log_plot_contour = log_plot_contour
        self._log_plot_edf = log_plot_edf
        self._log_plot_parallel_coordinate = log_plot_parallel_coordinate
        self._log_plot_param_importances = log_plot_param_importances
        self._log_plot_pareto_front = log_plot_pareto_front
        self._log_plot_slice = log_plot_slice
        self._log_plot_intermediate_values = log_plot_intermediate_values
        self._log_plot_optimization_history = log_plot_optimization_history

        run[INTEGRATION_VERSION_KEY] = __version__


    def __call__(self, study: optuna.Study, trial: optuna.trial.FrozenTrial):
        self._namespaces = get_namespaces(study, self._target_names)
        self._log_trial(study, trial)
        self._log_trial_distributions(trial)
        self._log_study_details(study, trial)
        self._log_plots(study, trial)
        self._log_study(study, trial)

    # is this for a single trial?
    def _log_trial(self, study, trial):
        _log_single_trial(self.run, study, trial=trial, namespaces=self._namespaces)

    def _log_trial_distributions(self, trial):
        self.run['study/distributions'].log(trial.distributions)


    def _log_study_details(self, study, trial):
        if trial._trial_id == 0:
            _log_study_details(self.run, study)

    def _log_plots(self, study, trial):
        if self._should_log_plots(study, trial):
            _log_plots(self.run, study,
                       namespaces=self._namespaces,
                       visualization_backend=self._visualization_backend,
                       log_plot_contour=self._log_plot_contour,
                       log_plot_edf=self._log_plot_edf,
                       log_plot_parallel_coordinate=self._log_plot_parallel_coordinate,
                       log_plot_param_importances=self._log_plot_param_importances,
                       log_plot_pareto_front=self._log_plot_pareto_front,
                       log_plot_slice=self._log_plot_slice,
                       log_plot_optimization_history=self._log_plot_optimization_history,
                       log_plot_intermediate_values=self._log_plot_intermediate_values,
                       )

    def _log_study(self, study, trial):
        if self._should_log_study(trial):
            _log_study(self.run, study)

    def _should_log_plots(self, study: optuna.study.Study, trial: optuna.trial.FrozenTrial):
        if not len(study.get_trials(states=(optuna.trial.TrialState.COMPLETE,))):
            return False
        elif self._plots_update_freq == 'never':
            return False
        else:
            if trial._trial_id % self._plots_update_freq == 0:
                return True
        return False

    def _should_log_study(self, trial: optuna.trial.FrozenTrial):
        if self._study_update_freq == 'never':
            return False
        if trial._trial_id % self._study_update_freq == 0:
            return True
        return False

    def log_best_trials(self, study: optuna.Study):
        _log_best_trials(self.run, study, namespaces=self._namespaces)

def _log_best_trials(run, study: optuna.Study, namespaces: List[str] = None):
    if study._is_multi_objective():
        if namespaces is None:
            namespaces = get_namespaces(study)
        _log_trials(run, study, trials=study.best_trials, namespaces=namespaces, best=True)
    else:
        _log_single_trial(run, study, trial=study.best_trial, namespaces=namespaces, best=True)


def get_namespaces(
    study: optuna.Study,
    target_names: List[str] = None
    ) -> Optional[List[str]]:

    if study._is_multi_objective():
        if target_names is None:
            return list(map(lambda direction_index: f'objective_{direction_index}', range(len(study.directions))))

        assert len(target_names) == len(study.directions), \
            """
            The target_names list must be th same length as study.directions.
            target_names length: {} != study.directions length: {}
            """.format(len(target_names), len(study.directions))
        return target_names
    else:
        if target_names is None:
            return 'Objective Value'
        assert len(target_names) == len(study.directions), \
            """
            The target_names list must be th same length as study.direction.
            target_names length: {} != study.directions length: {}
            """.format(len(target_names), len(study.directions))
        return target_names[0]


def log_study_metadata(study: optuna.Study,
                       run: neptune.Run,
                       base_namespace='',
                       target_names: List[str] = None,
                       log_plots=True,
                       log_study=True,
                       log_all_trials=True,
                       log_distributions=True,
                       visualization_backend='plotly',
                       log_plot_contour=True,
                       log_plot_edf=True,
                       log_plot_parallel_coordinate=True,
                       log_plot_param_importances=True,
                       log_plot_pareto_front=True,
                       log_plot_slice=True,
                       log_plot_intermediate_values=True,
                       log_plot_optimization_history=True):
    """A function that logs the metadata from Optuna Study to Neptune.

    With this function, you can log and display:

    * values and params for each trial
    * current best values and params for the study
    * visualizations from the `optuna.visualizations` module
    * parameter distributions for each trial
    * study object itself to load it later
    * and more

    Args:
        study(optuna.Study): Optuna study object.
        run(neptune.Run): Neptune Run.
        base_namespace(str, optional): Namespace inside the Run where your study metadata is logged. Defaults to ''.
        target_names(List[str], optional): List of objective names if `optuna.study` is multi-objective. Defaults to None.
        log_plots(bool): If 'True' the visualiztions from `optuna.visualizations` will be logged to Neptune.
            Defaults to 'True'.
        log_study(bool): If 'True' the study will be logged to Neptune. Depending on the study storage type used
            different objects are logged. If 'InMemoryStorage' is used the pickled study
            object will be logged to Neptune. Otherwise database URL will be logged. Defaults to 'True'.
        log_all_trials(bool): If 'True' all trials are logged. Defaults to 'True'.
        log_distributions(bool): If 'True' the distributions for all trials are logged. Defaults to 'True'.
        visualization_backend(str, optional): Which visualization backend is used for 'optuna.visualizations' plots.
            It can be one of 'matplotlib' or 'plotly'. Defaults to 'plotly'.
        log_plot_contour(bool, optional): If 'True' the `optuna.visualizations.plot_contour`
            visualization will be logged to Neptune. Defaults to `True`.
        log_plot_edf(bool, optional): If 'True' the `optuna.visualizations.plot_edf`
            visualization will be logged to Neptune. Defaults to `True`.
        log_plot_parallel_coordinate(bool, optional): If 'True' the `optuna.visualizations.plot_parallel_coordinate`
            visualization will be logged to Neptune. Defaults to `True`.
        log_plot_param_importances(bool, optional): If 'True' the `optuna.visualizations.plot_param_importances`
            visualization will be logged to Neptune. Defaults to `True`.
        log_plot_pareto_front(bool, optional): If 'True' the `optuna.visualizations.plot_pareto_front`
            visualization will be logged to Neptune.
            If your `optuna.study` is not multi-objective this plot is not logged. Defaults to `True`.
        log_plot_slice(bool, optional): If 'True' the `optuna.visualizations.plot_slice`
            visualization will be logged to Neptune. Defaults to `True`.
        log_plot_intermediate_values(bool, optional): If 'True' the `optuna.visualizations.plot_intermediate_values`
            visualization will be logged to Neptune.
            If your `optuna.study` is not using pruners this plot is not logged. Defaults to `True`. Defaults to `True`.
        log_plot_optimization_history(bool, optional): If 'True' the `optuna.visualizations.plot_optimization_history`
            visualization will be logged to Neptune. Defaults to `True`.

    Examples:
        Create a Run:
        >>> import neptune.new as neptune
        ... run = neptune.init('my_workspace/my_project')

        Create and run the Study:
        >>> study = optuna.create_study(direction='maximize')
        ... study.optimize(objective, n_trials=5)

        Log single and multi-objective Study metadata to Neptune:
        >>> import neptune.new.integrations.optuna as optuna_utils
        ... optuna_utils.log_study_metadata(study, run)

        Or `optionally` pass a list of objective names:
            Single-objective:
            ... optuna_utils.log_study_metadata(study, run, target_names=['accuracy'])
            Multi-objective:
            ... optuna_utils.log_study_metadata(study, run, target_names=['FLOPS', 'accuracy'])


    For more information, see `Neptune-Optuna integration docs page`_.
    .. _Neptune Optuna integration docs page:
       https://docs.neptune.ai/integrations-and-supported-tools/hyperparameter-optimization/optuna
    """
    run = run[base_namespace]

    namespaces = get_namespaces(study, target_names)

    _log_best_trials(run, study, namespaces)
    _log_study_details(run, study)


    if log_all_trials:
        _log_trials(run, study, study.trials, namespaces=namespaces)

    if log_distributions:
        run['study/distributions'].log([trial.distributions for trial in study.trials])

    if log_plots:
        _log_plots(run, study,
                   namespaces=namespaces,
                   visualization_backend=visualization_backend,
                   log_plot_contour=log_plot_contour,
                   log_plot_edf=log_plot_edf,
                   log_plot_parallel_coordinate=log_plot_parallel_coordinate,
                   log_plot_param_importances=log_plot_param_importances,
                   log_plot_pareto_front=log_plot_pareto_front,
                   log_plot_slice=log_plot_slice,
                   log_plot_optimization_history=log_plot_optimization_history,
                   log_plot_intermediate_values=log_plot_intermediate_values,
                   )

    if log_study:
        _log_study(run, study)


def load_study_from_run(run: neptune.Run):
    """A function that loads Optuna Study from an existing Neptune Run.

    Loading mechanics depends on the study storage type used during the Neptune Run:
    * if the study used 'InMemoryStorage', it will be loaded from the logged pickled Study object
    * if the study used database storage, it will be loaded from the logged database URL

    Args:
        run(neptune.Run): Neptune Run.

    Returns:
        optuna.Study

    Examples:
        Initialize an existing Run by passing Run ID:
        >>> import neptune.new as neptune
        ... run = neptune.init('my_workspace/my_project', run='PRO-123')

        Load study from a Run and continue optimization:
        >>> import neptune_optuna.impl as optuna_utils
        ... study = optuna_utils.load_study_from_run(run)
        ... study.optimize(objective, n_trials=20)

    For more information, see `Neptune-Optuna integration docs page`_.
    .. _Neptune Optuna integration docs page:
       https://docs.neptune.ai/integrations-and-supported-tools/hyperparameter-optimization/optuna
    """
    if run['study/storage_type'].fetch() == 'InMemoryStorage':
        return _get_pickle(path='study/study', run=run)
    else:
        return optuna.load_study(study_name=run['study/study_name'].fetch(), storage=run['study/storage_url'].fetch())


def _log_study_details(run, study: optuna.Study):
    run['study/study_name'] = study.study_name

    if study._is_multi_objective():
        run['study/directions'] = study.directions
    else:
        run['study/direction'] = study.direction

    run['study/system_attrs'] = study.system_attrs
    run['study/user_attrs'] = study.user_attrs
    with contextlib.suppress(AttributeError):
        run['study/_study_id'] = study._study_id
        run['study/_storage'] = study._storage


def _log_study(run, study: optuna.Study):
    with contextlib.suppress(AttributeError):
        if type(study._storage) is optuna.storages._in_memory.InMemoryStorage:
            """pickle and log the study object to the 'study/study.pkl' path"""
            run['study/study_name'] = study.study_name
            run['study/storage_type'] = 'InMemoryStorage'
            run['study/study'] = File.as_pickle(study)
        else:
            run['study/study_name'] = study.study_name
            if isinstance(study._storage, optuna.storages.RedisStorage):
                run['study/storage_type'] = "RedisStorage"
                run['study/storage_url'] = study._storage._url
            elif isinstance(study._storage, optuna.storages._CachedStorage):
                run['study/storage_type'] = "RDBStorage"  # apparently CachedStorage typically wraps RDBStorage
                run['study/storage_url'] = study._storage._backend.url
            elif isinstance(study._storage, optuna.storages.RDBStorage):
                run['study/storage_type'] = "RDBStorage"
                run['study/storage_url'] = study._storage.url
            else:
                run['study/storage_type'] = "unknown storage type"
                run['study/storage_url'] = "unknown storage url"


def _log_plots(run,
               study: optuna.Study,
               namespaces,
               visualization_backend='plotly',
               log_plot_contour=True,
               log_plot_edf=True,
               log_plot_parallel_coordinate=True,
               log_plot_param_importances=True,
               log_plot_pareto_front=True,
               log_plot_slice=True,
               log_plot_intermediate_values=True,
               log_plot_optimization_history=True,
               ):
    if visualization_backend == 'matplotlib':
        import optuna.visualization.matplotlib as vis
    elif visualization_backend == 'plotly':
        import optuna.visualization as vis
    else:
        raise NotImplementedError(f'{visualization_backend} visualisation backend is not implemented')

    handle = run['visualizations']

    for i in range(len(study.directions)):
        if isinstance(namespaces, list):
            target = lambda t: t.values[i]
            target_name = namespaces[i]
            temp_handle = handle[namespaces[i]]
        else:
            target = None
            target_name = namespaces
            temp_handle = handle


        if vis.is_available:
            params = [p_name for t in study.trials for p_name in t.params.keys()]

            if log_plot_contour and any(params):
                temp_handle['plot_contour'] = neptune.types.File.as_html(vis.plot_contour(study, target=target, target_name=target_name))

            if log_plot_edf:
                temp_handle['plot_edf'] = neptune.types.File.as_html(vis.plot_edf(study, target=target, target_name=target_name))

            if log_plot_parallel_coordinate:
                temp_handle['plot_parallel_coordinate'] = \
                    neptune.types.File.as_html(vis.plot_parallel_coordinate(study, target=target, target_name=target_name))

            if log_plot_param_importances and len(study.get_trials(states=(optuna.trial.TrialState.COMPLETE, optuna.trial.TrialState.PRUNED,))) > 1:
                with contextlib.suppress(RuntimeError, ValueError, ZeroDivisionError):
                    temp_handle['plot_param_importances'] = neptune.types.File.as_html(vis.plot_param_importances(study, target=target, target_name=target_name))
            if log_plot_slice and any(params):
                temp_handle['plot_slice'] = neptune.types.File.as_html(vis.plot_slice(study, target=target, target_name=target_name))

            if log_plot_intermediate_values and any(trial.intermediate_values for trial in study.trials):
                # Intermediate values plot if available only if the above condition is met
                temp_handle['plot_intermediate_values'] = \
                    neptune.types.File.as_html(vis.plot_intermediate_values(study, target=target, target_name=target_name))

            if log_plot_optimization_history:
                temp_handle['plot_optimization_history'] = \
                    neptune.types.File.as_html(vis.plot_optimization_history(study, target=target, target_name=target_name))

    if vis.is_available and log_plot_pareto_front and study._is_multi_objective() and visualization_backend == 'plotly':
        handle['plot_pareto_front'] = neptune.types.File.as_html(vis.plot_pareto_front(study, target_names=namespaces))


def _log_single_trial(run, study: optuna.Study, trial: optuna.trial.FrozenTrial, namespaces, best=False):
    handle = run['best'] if best else run['trials']

    handle[f'trials/{trial._trial_id}/datetime_start'] = trial.datetime_start
    handle[f'trials/{trial._trial_id}/datetime_complete'] = trial.datetime_complete
    handle[f'trials/{trial._trial_id}/duration'] = trial.duration
    handle[f'trials/{trial._trial_id}/distributions'] = trial.distributions
    handle[f'trials/{trial._trial_id}/intermediate_values'] = trial.intermediate_values
    handle[f'trials/{trial._trial_id}/params'] = trial.params

    if study._is_multi_objective():
        handle[f'trials/{trial._trial_id}/values'] = {f'{namespaces[k]}': v for k, v in enumerate(trial.values)}

    else:
        handle[f'trials/{trial._trial_id}/value'] = trial.value

        if best:
            handle['value'] = trial.value
            handle['param'] = trial.params
            handle['value|param'] = f'value: {trial.value}| params: {trial.params}'
        else:
            handle['values'].log(trial.value, step=trial._trial_id)
            handle['params'].log(trial.params)
            handle['values|params'].log(f'value: {trial.value}| params: {trial.params}')

    if trial.state.is_finished() and trial.state != optuna.trial.TrialState.COMPLETE:
        handle[f'trials/{trial._trial_id}/state'] = repr(trial.state)


def _log_trials(run, study: optuna.Study, trials: Iterable[optuna.trial.FrozenTrial], namespaces, best=False):
    if not study.best_trials and best:
        return dict()
    for trial in trials:
        _log_single_trial(run, study, trial, namespaces, best=best)


def _get_pickle(run: neptune.Run, path: str):
    import os
    import tempfile
    import pickle

    with tempfile.TemporaryDirectory() as d:
        run[path].download(destination=d)
        filepath = os.listdir(d)[0]
        full_path = os.path.join(d, filepath)
        with open(full_path, 'rb') as file:
            artifact = pickle.load(file)

    return artifact
