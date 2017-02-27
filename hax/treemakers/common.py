"""Standard variables for most analyses
"""
from hax.minitrees import TreeMaker
from collections import defaultdict


class Fundamentals(TreeMaker):
    """Simple minitree containing basic information about every event, regardless of its contents.
    This minitree is always loaded whether you like it or not :-)

    Provides:
     - run_number: Run number of the run/dataset this event came from (common to all treemakers)
     - event_number: Event number within the dataset (common to all treemakers)
     - event_time: Unix time (in ns since the unix epoch) of the start of the event window
     - event_duration: duration (in ns) of the event
    """
    __version__ = '0.1'
    pax_version_independent = True
    branch_selection = ['event_number', 'start_time', 'stop_time']

    def extract_data(self, event):
        return dict(event_time=event.start_time,
                    event_duration=event.stop_time - event.start_time)


class Basics(TreeMaker):
    """Basic information needed in most (standard) analyses, mostly on the main interaction.

    Provides:
     - s1: The uncorrected area in pe of the main interaction's S1
     - s2: The uncorrected area in pe of the main interaction's S2
     - cs1: The corrected area in pe of the main interaction's S1
     - cs2: The corrected area in pe of the main interaction's S2
     - x: The x-position of the main interaction (primary algorithm chosen by pax, currently TopPatternFit)
     - y: The y-position of the main interaction
     - z: The z-position of the main interaction (computed by pax using configured drift velocity)
     - drift_time: The drift time in ns (pax units) of the main interaction
     - s1_area_fraction_top: The fraction of uncorrected area in the main interaction's S1 seen by the top array
     - s2_area_fraction_top: The fraction of uncorrected area in the main interaction's S2 seen by the top array
     - s1_range_50p_area: The width of the s1 (ns), duration of region that contains 50% of the area of the peak
     - s2_range_50p_area: The width of the s2 (ns), duration of region that contains 50% of the area of the peak
     - largest_other_s1: The uncorrected area in pe of the largest S1 in the TPC not in the main interaction
     - largest_other_s2: The uncorrected area in pe of the largest S2 in the TPC not in the main interaction
     - largest_veto: The uncorrected area in pe of the largest non-lone_hit peak in the veto
     - largest_unknown: The largest TPC peak of type 'unknown'
     - largest_coincidence: The largest TPC peak of type 'coincidence'

    Notes:
     * 'largest' refers to uncorrected area.
     * 'uncorrected' refers to the area in pe without applying any position- or saturation corrections.
     * 'corrected' refers to applying all available position- and/or saturation corrections
       (see https://github.com/XENON1T/pax/blob/master/pax/plugins/interaction_processing/BuildInteractions.py#L105)
     * 'main interaction' is event.interactions[0], which is determined by pax
                          (currently just the largest S1 + largest S2 after it)

    """
    __version__ = '0.1'

    def extract_data(self, event):
        event_data = dict()

        # Detect events without at least one S1 + S2 pair immediately
        # We cannot even fill the basic variables for these
        if len(event.interactions) != 0:

            # Extract basic data: useful in any analysis
            interaction = event.interactions[0]
            s1 = event.peaks[interaction.s1]
            s2 = event.peaks[interaction.s2]
            event_data.update(dict(s1=s1.area,
                                   s2=s2.area,
                                   s1_area_fraction_top=s1.area_fraction_top,
                                   s2_area_fraction_top=s2.area_fraction_top,
                                   s1_range_50p_area=s1.range_area_decile[5],
                                   s2_range_50p_area=s2.range_area_decile[5],
                                   cs1=s1.area * interaction.s1_area_correction,
                                   cs2=s2.area * interaction.s2_area_correction,
                                   x=interaction.x,
                                   y=interaction.y,
                                   z=interaction.z,
                                   drift_time=interaction.drift_time))

            exclude_peaks_from_double_sc = [interaction.s1, interaction.s2]
        else:
            exclude_peaks_from_double_sc = []

        # Add double scatter cut data: area of the second largest peak of each peak type.
        # Note we explicitly differentiate non-tpc peaks here; in interaction objects this is already taken care of.
        largest_area_of_type = defaultdict(float)
        for i, p in enumerate(event.peaks):
            if i in exclude_peaks_from_double_sc:
                continue
            if p.detector == 'tpc':
                peak_type = p.type
            else:
                if p.type == 'lone_hit':
                    peak_type = 'lone_hit_%s' % p.detector    # Will not be saved
                else:
                    peak_type = p.detector
            largest_area_of_type[peak_type] = max(p.area, largest_area_of_type[peak_type])

        event_data.update(dict(largest_other_s1=largest_area_of_type['s1'],
                               largest_other_s2=largest_area_of_type['s2'],
                               largest_veto=largest_area_of_type['veto'],
                               largest_unknown=largest_area_of_type['unknown'],
                               largest_coincidence=largest_area_of_type['coincidence']))

        return event_data


class LargestPeakProperties(TreeMaker):
    """Largest peak properties for each type and for all peaks.
    If you're doing an S1-only or S2-only analysis, you'll want this info instead of Basics.
    In other case you may want to combine this and Basics.
    """
    extra_branches = ['peaks.n_hits', 'peaks.hit_time_std', 'peaks.center_time',
                      'peaks.n_saturated_channels', 'peaks.n_contributing_channels']
    peak_types = ['s1', 's2', 'lone_hit', 'unknown']
    __version__ = '0.1'

    # Simple peak properties to get. Logic for range_x0p_area and xy is separate.
    peak_properties_to_get = ['area', 'area_fraction_top',
                              'n_hits', 'hit_time_std', 'center_time',
                              'n_saturated_channels', 'n_contributing_channels']

    def get_properties(self, peak=None, prefix=''):
        """Return dictionary with peak properties, keys prefixed with prefix
        if peak is None, will return nans for all values
        """
        if peak is None:
            return {prefix + k: float('nan') for k in
                    self.peak_properties_to_get + ['range_50p_area', 'range_90p_area', 'x', 'y']}
        result = {field: getattr(peak, field) for field in self.peak_properties_to_get}
        result['range_50p_area'] = peak.range_area_decile[5]
        result['range_90p_area'] = peak.range_area_decile[9]
        for rp in peak.reconstructed_positions:
            if rp.algorithm == 'PosRecTopPatternFit':
                result['x'] = rp.x
                result['y'] = rp.y
        return {prefix + k: v for k, v in result.items()}

    def extract_data(self, event):  # This runs on each event
        peaks = event.peaks

        # Get the largest peak of each type, and the largest peak overall
        largest_peak_per_type = {}              # peak type: (index, area) of largest peak seen so far
        for p_i, p in enumerate(peaks):
            if p.detector != 'tpc':
                continue
            for p_type in (p.type, 'largest'):
                if p.area > largest_peak_per_type.get(p_type, (None, 0))[1]:
                    # New largest peak of this peak type
                    largest_peak_per_type[p_type] = (p_i, p.area)

        result = {}
        for p_type in self.peak_types:
            upd = self.get_properties(peak=peaks[largest_peak_per_type[p_type][0]]
                                           if p_type in largest_peak_per_type else None,
                                      prefix=p_type + '_')
            result.update(upd)

        return result


class TotalProperties(TreeMaker):
    """Aggregate properties of signals in the entire event

    Provides:
     - n_pulses, the total number of raw pulses in the event (for pax versions >6.0.0)
     - n_peaks, the total number of TPC peaks in the event (including lone hits)
     - n_true_peaks, the total number of TPC peaks in the event to which at least two PMTs contribute
     - total_peak_area, the total area (pe) in all TPC peaks in the event
     - area_before_main_s2, same, but including only peaks that occur before the main s2 (if there is one, else 0)
    """
    __version__ = '0.2.0'
    branch_selection = ['peaks.area', 'n_pulses', 'peaks.detector', 'interactions.s2', 'peaks.left', 'peaks.type']

    def extract_data(self, event):
        peaks = event.peaks
        result = dict(n_pulses=event.n_pulses,
                      n_peaks=len(peaks))
        result['n_true_peaks'] = len([True for p in peaks if p.type != 'lone_hit'])
        result['total_peak_area'] = sum([p.area
                                         for p in peaks
                                         if p.detector == 'tpc'])
        if len(event.interactions):
            main_s2_left = peaks[event.interactions[0].s2].left
            result['area_before_main_s2'] = sum([p.area
                                                 for p in peaks
                                                 if p.detector == 'tpc' and p.left < main_s2_left])
        else:
            result['area_before_main_s2'] = 0

        return result