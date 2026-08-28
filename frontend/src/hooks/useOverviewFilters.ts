import { useState, useEffect, useRef, useMemo } from 'react';
import type { MetadataResponse, FilterRequest } from '../types';
import { clampDate, defaultDateRange } from '../utils/dateRange';

export interface OverviewFiltersState {
  selectedHostname: string;
  startDate: string;
  endDate: string;
  selectedPartitions: string[];
  selectedAccounts: string[];
  selectedUsers: string[];
  selectedQos: string[];
  selectedStates: string[];
  colorBy: string;
  accountSegments: number;
  periodType: string;
  hideUnusedNodes: boolean;
  sortByUsage: boolean;
  normalizeNodeUsage: boolean;
}

export interface OverviewFiltersActions {
  setSelectedHostname: (value: string) => void;
  setStartDate: (value: string) => void;
  setEndDate: (value: string) => void;
  setSelectedPartitions: (value: string[]) => void;
  setSelectedAccounts: (value: string[]) => void;
  setSelectedUsers: (value: string[]) => void;
  setSelectedQos: (value: string[]) => void;
  setSelectedStates: (value: string[]) => void;
  setColorBy: (value: string) => void;
  setAccountSegments: (value: number) => void;
  setPeriodType: (value: string) => void;
  setHideUnusedNodes: (value: boolean) => void;
  setSortByUsage: (value: boolean) => void;
  setNormalizeNodeUsage: (value: boolean) => void;
}

export interface UseOverviewFiltersResult {
  state: OverviewFiltersState;
  actions: OverviewFiltersActions;
  actualPeriodType: string;
  filterRequest: FilterRequest;
}

function calculatePeriodType(start: string, end: string): string {
  if (!start || !end) return 'month';

  const startDate = new Date(start);
  const endDate = new Date(end);
  const diffTime = Math.abs(endDate.getTime() - startDate.getTime());
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

  if (diffDays <= 60) {
    return 'day';
  } else if (diffDays <= 180) {
    return 'week';
  } else if (diffDays <= 730) {
    return 'month';
  } else {
    return 'year';
  }
}

export function useOverviewFilters(
  allClustersMetadata: MetadataResponse | undefined
): UseOverviewFiltersResult {
  const [selectedHostname, setSelectedHostname] = useState<string>('');
  const previousHostname = useRef<string>('');
  const [startDate, setStartDateState] = useState<string>('');
  const [endDate, setEndDateState] = useState<string>('');
  const [selectedPartitions, setSelectedPartitions] = useState<string[]>([]);
  const [selectedAccounts, setSelectedAccounts] = useState<string[]>([]);
  const [selectedUsers, setSelectedUsers] = useState<string[]>([]);
  const [selectedQos, setSelectedQos] = useState<string[]>([]);
  const [selectedStates, setSelectedStates] = useState<string[]>([]);
  const [colorBy, setColorBy] = useState<string>('');
  const [accountSegments, setAccountSegments] = useState<number>(3);
  const [periodType, setPeriodType] = useState<string>('auto');
  const [hideUnusedNodes, setHideUnusedNodes] = useState<boolean>(true);
  const [sortByUsage, setSortByUsage] = useState<boolean>(false);
  const [normalizeNodeUsage, setNormalizeNodeUsage] = useState<boolean>(false);

  const dateRange = allClustersMetadata?.date_ranges[selectedHostname] ?? null;
  // Dates typed or picked by the user are kept inside the cluster's data range
  const setStartDate = (value: string) => setStartDateState(clampDate(value, dateRange));
  const setEndDate = (value: string) => setEndDateState(clampDate(value, dateRange));

  const actualPeriodType = periodType === 'auto'
    ? calculatePeriodType(startDate, endDate)
    : periodType;

  // Set initial hostname and dates when metadata loads
  useEffect(() => {
    if (allClustersMetadata && allClustersMetadata.hostnames.length > 0 && !selectedHostname) {
      const firstHostname = allClustersMetadata.hostnames[0];
      setSelectedHostname(firstHostname);

      const initial = defaultDateRange(allClustersMetadata.date_ranges[firstHostname]);
      if (initial) {
        setStartDateState(initial.start);
        setEndDateState(initial.end);
      }
    }
  }, [allClustersMetadata, selectedHostname]);

  // Update dates when hostname changes
  useEffect(() => {
    if (selectedHostname && selectedHostname !== previousHostname.current) {
      const initial = defaultDateRange(allClustersMetadata?.date_ranges[selectedHostname]);
      if (initial) {
        setStartDateState(initial.start);
        setEndDateState(initial.end);
      }
      // Reset filters when changing hostname
      setSelectedPartitions([]);
      setSelectedAccounts([]);
      setSelectedUsers([]);
      setSelectedQos([]);
      setSelectedStates([]);

      previousHostname.current = selectedHostname;
    }
  }, [selectedHostname, allClustersMetadata]);

  const filterRequest: FilterRequest = useMemo(() => ({
    hostname: selectedHostname,
    start_date: startDate,
    end_date: endDate,
    partitions: selectedPartitions.length > 0 ? selectedPartitions : undefined,
    accounts: selectedAccounts.length > 0 ? selectedAccounts : undefined,
    users: selectedUsers.length > 0 ? selectedUsers : undefined,
    qos: selectedQos.length > 0 ? selectedQos : undefined,
    states: selectedStates.length > 0 ? selectedStates : undefined,
    period_type: actualPeriodType,
    color_by: colorBy || undefined,
    account_segments: accountSegments > 0 ? accountSegments : undefined,
  }), [
    selectedHostname, startDate, endDate, selectedPartitions, selectedAccounts,
    selectedUsers, selectedQos, selectedStates, actualPeriodType, colorBy, accountSegments
  ]);

  return {
    state: {
      selectedHostname,
      startDate,
      endDate,
      selectedPartitions,
      selectedAccounts,
      selectedUsers,
      selectedQos,
      selectedStates,
      colorBy,
      accountSegments,
      periodType,
      hideUnusedNodes,
      sortByUsage,
      normalizeNodeUsage,
    },
    actions: {
      setSelectedHostname,
      setStartDate,
      setEndDate,
      setSelectedPartitions,
      setSelectedAccounts,
      setSelectedUsers,
      setSelectedQos,
      setSelectedStates,
      setColorBy,
      setAccountSegments,
      setPeriodType,
      setHideUnusedNodes,
      setSortByUsage,
      setNormalizeNodeUsage,
    },
    actualPeriodType,
    filterRequest,
  };
}
