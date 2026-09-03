import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { dashboardApi, reportsApi, authApi } from '../api/client';
import Header from '../components/Header';
import Footer from '../components/Footer';
import Filters from '../components/Filters';
import StatsCards from '../components/StatsCards';
import Charts from '../components/Charts';
import ReportControls from '../components/ReportControls';
import ReportPreview from '../components/ReportPreview';
import { useOverviewFilters } from '../hooks/useOverviewFilters';
import { useReportFilters } from '../hooks/useReportFilters';
import type { ReportData } from '../components/ReportPreview';

const Dashboard: React.FC = () => {
  const [sidebarHidden, setSidebarHidden] = useState<boolean>(() => {
    try {
      return localStorage.getItem('sidebar_hidden') === '1';
    } catch {
      return false;
    }
  });
  const toggleSidebar = () => {
    setSidebarHidden((hidden) => {
      try {
        localStorage.setItem('sidebar_hidden', hidden ? '0' : '1');
      } catch {
        // storage unavailable; the toggle still works for this page
      }
      return !hidden;
    });
  };

  const [activeTab, setActiveTab] = useState<'overview' | 'reports'>('overview');

  // Fetch current user info to check admin status
  const { data: userInfo } = useQuery({
    queryKey: ['currentUser'],
    queryFn: authApi.getCurrentUser,
  });


  // Fetch full cluster list (never filtered by hostname)
  const { data: allClustersMetadata } = useQuery({
    queryKey: ['allClusters'],
    queryFn: () => dashboardApi.getMetadata({}),
    refetchOnMount: true,
    staleTime: 0,
    placeholderData: (previousData) => previousData,
  });

  // Overview filters hook
  const { state: overviewState, actions: overviewActions, actualPeriodType, filterRequest } =
    useOverviewFilters(allClustersMetadata);

  // Fetch metadata - refetch when hostname or date range changes to update filter options
  const { data: metadata, isLoading: metadataLoading } = useQuery({
    queryKey: ['metadata', overviewState.selectedHostname, overviewState.startDate, overviewState.endDate],
    queryFn: () => dashboardApi.getMetadata({
      hostname: overviewState.selectedHostname || undefined,
      start_date: overviewState.startDate || undefined,
      end_date: overviewState.endDate || undefined,
    }),
    refetchOnMount: true,
    staleTime: 0,
    placeholderData: (previousData) => previousData,
  });

  // Report filters hook
  const { state: reportState, actions: reportActions, availableYears } =
    useReportFilters(metadata, activeTab, overviewState.selectedHostname);

  // Combine metadata: use full cluster list from allClustersMetadata, but filtered data from metadata
  const combinedMetadata = useMemo(() => {
    if (!allClustersMetadata) return metadata;
    if (!metadata) return allClustersMetadata;

    return {
      ...metadata,
      hostnames: allClustersMetadata.hostnames,
      date_ranges: {
        ...allClustersMetadata.date_ranges,
        ...metadata.date_ranges,
      },
    };
  }, [allClustersMetadata, metadata]);

  // Fetch report preview
  const {
    data: reportData,
    isLoading: reportLoading,
    error: reportError,
  } = useQuery<ReportData>({
    queryKey: ['reportPreview', reportState.reportHostname, reportState.reportType,
               reportState.selectedYear, reportState.selectedMonth, reportState.selectedQuarter],
    queryFn: () => reportsApi.previewReport(
      reportState.reportHostname,
      reportState.reportType,
      reportState.selectedYear,
      reportState.reportType === 'monthly' ? reportState.selectedMonth : undefined,
      reportState.reportType === 'quarterly' ? reportState.selectedQuarter : undefined
    ),
    enabled: !!reportState.reportHostname && activeTab === 'reports',
  });

  const handleDownloadReport = () => {
    reportsApi.downloadReport(
      reportState.reportHostname,
      reportState.reportType,
      reportState.selectedYear,
      reportState.reportType === 'monthly' ? reportState.selectedMonth : undefined,
      reportState.reportType === 'quarterly' ? reportState.selectedQuarter : undefined,
      reportState.downloadFormat
    );
  };

  // Fetch aggregated chart data
  const {
    data: chartsData,
    isLoading: dataLoading,
    error: dataError,
  } = useQuery({
    queryKey: ['aggregatedCharts', filterRequest],
    queryFn: async () => {
      return await dashboardApi.getAggregatedCharts(filterRequest);
    },
    enabled: !!overviewState.selectedHostname,
  });

  if (metadataLoading) {
    return (
      <div className="app">
        <Header userInfo={userInfo}  />
        <div className="container">
          <div className="loading-screen">
            <div className="loading-spinner"></div>
            <h2>Loading Dashboard...</h2>
            <p>Fetching cluster metadata from backend</p>
          </div>
        </div>
        <Footer />
      </div>
    );
  }

  if (!metadata || metadata.hostnames.length === 0) {
    return (
      <div className="app">
        <Header userInfo={userInfo}  />
        <div className="container">
          <div className="error-screen">
            <h2>No Data Available</h2>
            <p>No cluster data found. Please ensure data files are in the correct location.</p>
          </div>
        </div>
        <Footer />
      </div>
    );
  }

  return (
    <div className="app">
      <Header activeTab={activeTab} onTabChange={setActiveTab} userInfo={userInfo}  />
      <div className="dashboard-layout">
        <button
          type="button"
          className="sidebar-toggle"
          onClick={toggleSidebar}
          title={sidebarHidden ? 'Show filters' : 'Hide filters'}
          aria-label={sidebarHidden ? 'Show filters' : 'Hide filters'}
        >
          {sidebarHidden ? '\u203A' : '\u2039'}
        </button>
        <div className={sidebarHidden ? 'sidebar sidebar-hidden' : 'sidebar'}>
          {activeTab === 'overview' ? (
            <Filters
              metadata={combinedMetadata}
              selectedHostname={overviewState.selectedHostname}
              setSelectedHostname={overviewActions.setSelectedHostname}
              startDate={overviewState.startDate}
              setStartDate={overviewActions.setStartDate}
              endDate={overviewState.endDate}
              setEndDate={overviewActions.setEndDate}
              selectedPartitions={overviewState.selectedPartitions}
              setSelectedPartitions={overviewActions.setSelectedPartitions}
              selectedAccounts={overviewState.selectedAccounts}
              setSelectedAccounts={overviewActions.setSelectedAccounts}
              selectedUsers={overviewState.selectedUsers}
              setSelectedUsers={overviewActions.setSelectedUsers}
              selectedQos={overviewState.selectedQos}
              setSelectedQos={overviewActions.setSelectedQos}
              selectedStates={overviewState.selectedStates}
              setSelectedStates={overviewActions.setSelectedStates}
              colorBy={overviewState.colorBy}
              setColorBy={overviewActions.setColorBy}
              accountSegments={overviewState.accountSegments}
              setAccountSegments={overviewActions.setAccountSegments}
              isAdmin={userInfo?.is_admin ?? false}
              periodType={overviewState.periodType}
              setPeriodType={overviewActions.setPeriodType}
              currentPeriodType={actualPeriodType}
              hideUnusedNodes={overviewState.hideUnusedNodes}
              setHideUnusedNodes={overviewActions.setHideUnusedNodes}
              sortByUsage={overviewState.sortByUsage}
              setSortByUsage={overviewActions.setSortByUsage}
              normalizeNodeUsage={overviewState.normalizeNodeUsage}
              setNormalizeNodeUsage={overviewActions.setNormalizeNodeUsage}
            />
          ) : (
            <ReportControls
              metadata={metadata}
              reportHostname={reportState.reportHostname}
              setReportHostname={reportActions.setReportHostname}
              reportType={reportState.reportType}
              setReportType={reportActions.setReportType}
              selectedYear={reportState.selectedYear}
              setSelectedYear={reportActions.setSelectedYear}
              selectedMonth={reportState.selectedMonth}
              setSelectedMonth={reportActions.setSelectedMonth}
              selectedQuarter={reportState.selectedQuarter}
              setSelectedQuarter={reportActions.setSelectedQuarter}
              downloadFormat={reportState.downloadFormat}
              setDownloadFormat={reportActions.setDownloadFormat}
              onDownload={handleDownloadReport}
              availableYears={availableYears}
            />
          )}
        </div>
        <div className="main-content">
          {activeTab === 'overview' ? (
            <>
              {dataError && (
                <div className="error">
                  Error loading data: {dataError instanceof Error ? dataError.message : 'Unknown error'}
                </div>
              )}

              {dataLoading ? (
                <div className="loading-screen">
                  <div className="loading-spinner"></div>
                  <h2>Loading Charts...</h2>
                  <p>Aggregating data for {overviewState.selectedHostname}</p>
                  <p className="loading-detail">Period: {overviewState.startDate} to {overviewState.endDate} ({actualPeriodType})</p>
                </div>
              ) : (
                <>
                  <StatsCards data={chartsData} />
                  <Charts
                    data={chartsData}
                    hideUnusedNodes={overviewState.hideUnusedNodes}
                    sortByUsage={overviewState.sortByUsage}
                    normalizeNodeUsage={overviewState.normalizeNodeUsage}
                    colorBy={overviewState.colorBy}
                    periodType={actualPeriodType}
                  />
                </>
              )}
            </>
          ) : (
            <ReportPreview
              reportData={reportData}
              isLoading={reportLoading}
              error={reportError}
              reportType={reportState.reportType}
            />
          )}
        </div>
      </div>
      <Footer />
    </div>
  );
};

export default Dashboard;
