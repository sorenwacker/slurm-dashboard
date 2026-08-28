import React, { useState } from 'react';
import type { MetadataResponse } from '../types';

// Helper function to filter items based on search
const filterItems = (items: string[], search: string): string[] => {
  if (!search.trim()) return items;
  return items.filter(item =>
    item.toLowerCase().includes(search.toLowerCase())
  );
};

// Helper to toggle item selection
const toggleItem = (item: string, selected: string[], setter: (items: string[]) => void) => {
  if (selected.includes(item)) {
    setter(selected.filter(i => i !== item));
  } else {
    setter([...selected, item]);
  }
};

// Component for searchable checkbox list with collapse (moved outside to prevent recreation)
const SearchableCheckboxList: React.FC<{
  label: string;
  items: string[];
  selected: string[];
  setSelected: (items: string[]) => void;
  search: string;
  setSearch: (search: string) => void;
  isExpanded: boolean;
  setIsExpanded: (expanded: boolean) => void;
}> = ({ label, items, selected, setSelected, search, setSearch, isExpanded, setIsExpanded }) => {
  const filteredItems = filterItems(items, search);
  const allFiltered = filteredItems.length === selected.filter(s => filteredItems.includes(s)).length && filteredItems.length > 0;

  const toggleAll = () => {
    if (allFiltered) {
      setSelected(selected.filter(s => !filteredItems.includes(s)));
    } else {
      setSelected([...new Set([...selected, ...filteredItems])]);
    }
  };

  return (
    <div className="filter-group">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
        <div
          onClick={() => setIsExpanded(!isExpanded)}
          style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', flex: 1 }}
        >
          <span style={{ marginRight: '0.35rem', fontSize: '0.8rem' }}>
            {isExpanded ? '▼' : '▶'}
          </span>
          <label style={{ cursor: 'pointer', margin: 0, fontSize: '0.8rem' }}>{label}</label>
          {selected.length > 0 && (
            <span style={{
              marginLeft: '0.35rem',
              fontSize: '0.7rem',
              color: '#6366f1',
              fontWeight: 'bold'
            }}>
              ({selected.length})
            </span>
          )}
        </div>
        {selected.length > 0 && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setSelected([]);
            }}
            style={{
              fontSize: '0.65rem',
              padding: '0.15rem 0.35rem',
              background: '#dc3545',
              color: 'white',
              border: 'none',
              borderRadius: '3px',
              cursor: 'pointer',
            }}
          >
            Clear
          </button>
        )}
      </div>
      {isExpanded && (
        <>
          <input
            type="text"
            placeholder={`Search ${label.toLowerCase()}...`}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              width: '100%',
              padding: '0.35rem',
              borderRadius: '4px',
              border: '1px solid var(--border)',
              fontSize: '0.8rem',
              marginBottom: '0.35rem',
              background: 'var(--bg-secondary)',
              color: 'var(--text-primary)',
            }}
          />
          <div style={{
            maxHeight: '180px',
            overflowY: 'auto',
            border: '1px solid var(--border)',
            borderRadius: '4px',
            padding: '0.35rem',
            background: 'var(--bg-secondary)',
          }}>
            {filteredItems.length > 1 && (
              <label style={{ display: 'flex', alignItems: 'center', padding: '0.15rem 0', cursor: 'pointer', fontWeight: 'bold', borderBottom: '1px solid var(--border)', marginBottom: '0.15rem', fontSize: '0.75rem' }}>
                <input
                  type="checkbox"
                  checked={allFiltered}
                  onChange={toggleAll}
                  style={{ marginRight: '0.35rem' }}
                />
                Select All ({filteredItems.length})
              </label>
            )}
            {filteredItems.length === 0 && (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', padding: '0.35rem', textAlign: 'center' }}>
                No items found
              </div>
            )}
            {filteredItems.map((item) => (
              <label key={item} style={{ display: 'flex', alignItems: 'center', padding: '0.12rem 0', cursor: 'pointer', fontSize: '0.75rem' }}>
                <input
                  type="checkbox"
                  checked={selected.includes(item)}
                  onChange={() => toggleItem(item, selected, setSelected)}
                  style={{ marginRight: '0.35rem' }}
                />
                {item}
              </label>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

interface FiltersProps {
  metadata: MetadataResponse | undefined;
  selectedHostname: string;
  setSelectedHostname: (hostname: string) => void;
  startDate: string;
  setStartDate: (date: string) => void;
  endDate: string;
  setEndDate: (date: string) => void;
  selectedPartitions: string[];
  setSelectedPartitions: (partitions: string[]) => void;
  selectedAccounts: string[];
  setSelectedAccounts: (accounts: string[]) => void;
  selectedUsers: string[];
  setSelectedUsers: (users: string[]) => void;
  selectedQos: string[];
  setSelectedQos: (qos: string[]) => void;
  selectedStates: string[];
  setSelectedStates: (states: string[]) => void;
  colorBy: string;
  setColorBy: (colorBy: string) => void;
  accountSegments: number;
  setAccountSegments: (segments: number) => void;
  periodType: string;
  setPeriodType: (periodType: string) => void;
  currentPeriodType: string;
  isAdmin: boolean;
}

const Filters: React.FC<FiltersProps> = ({
  metadata,
  selectedHostname,
  setSelectedHostname,
  startDate,
  setStartDate,
  endDate,
  setEndDate,
  selectedPartitions,
  setSelectedPartitions,
  selectedAccounts,
  setSelectedAccounts,
  selectedUsers,
  setSelectedUsers,
  selectedQos,
  setSelectedQos,
  selectedStates,
  setSelectedStates,
  colorBy,
  setColorBy,
  accountSegments,
  setAccountSegments,
  periodType,
  setPeriodType,
  currentPeriodType,
  isAdmin,
}) => {
  // Individual collapse states for each filter category
  const [isPartitionsExpanded, setIsPartitionsExpanded] = useState(false);
  const [isAccountsExpanded, setIsAccountsExpanded] = useState(false);
  const [isUsersExpanded, setIsUsersExpanded] = useState(false);
  const [isQosExpanded, setIsQosExpanded] = useState(false);
  const [isStatesExpanded, setIsStatesExpanded] = useState(false);

  // Search states for each filter
  const [partitionSearch, setPartitionSearch] = useState('');
  const [accountSearch, setAccountSearch] = useState('');
  const [userSearch, setUserSearch] = useState('');
  const [qosSearch, setQosSearch] = useState('');
  const [stateSearch, setStateSearch] = useState('');

  // Global search for selecting across all categories
  const [globalSearch, setGlobalSearch] = useState('');

  const dateRange = metadata && selectedHostname ? metadata.date_ranges[selectedHostname] : null;

  const hasActiveFilters =
    selectedPartitions.length > 0 ||
    selectedAccounts.length > 0 ||
    selectedUsers.length > 0 ||
    selectedQos.length > 0 ||
    selectedStates.length > 0;

  const clearAllFilters = () => {
    setSelectedPartitions([]);
    setSelectedAccounts([]);
    setSelectedUsers([]);
    setSelectedQos([]);
    setSelectedStates([]);
  };

  // Select all items matching the global search pattern across all categories
  const selectAllMatching = () => {
    if (!globalSearch.trim() || !metadata || !selectedHostname) return;

    const pattern = globalSearch.toLowerCase();

    // Find matching items in each category
    const matchingPartitions = (metadata.partitions[selectedHostname] || [])
      .filter(item => item.toLowerCase().includes(pattern));
    const matchingAccounts = (metadata.accounts[selectedHostname] || [])
      .filter(item => item.toLowerCase().includes(pattern));
    const matchingUsers = (metadata.users[selectedHostname] || [])
      .filter(item => item.toLowerCase().includes(pattern));
    const matchingQos = (metadata.qos[selectedHostname] || [])
      .filter(item => item.toLowerCase().includes(pattern));
    const matchingStates = (metadata.states[selectedHostname] || [])
      .filter(item => item.toLowerCase().includes(pattern));

    // Add matching items to existing selections (union)
    setSelectedPartitions([...new Set([...selectedPartitions, ...matchingPartitions])]);
    setSelectedAccounts([...new Set([...selectedAccounts, ...matchingAccounts])]);
    setSelectedUsers([...new Set([...selectedUsers, ...matchingUsers])]);
    setSelectedQos([...new Set([...selectedQos, ...matchingQos])]);
    setSelectedStates([...new Set([...selectedStates, ...matchingStates])]);
  };

  // Count how many items match the global search
  const countMatching = (): number => {
    if (!globalSearch.trim() || !metadata || !selectedHostname) return 0;

    const pattern = globalSearch.toLowerCase();
    let count = 0;

    count += (metadata.partitions[selectedHostname] || []).filter(item => item.toLowerCase().includes(pattern)).length;
    count += (metadata.accounts[selectedHostname] || []).filter(item => item.toLowerCase().includes(pattern)).length;
    count += (metadata.users[selectedHostname] || []).filter(item => item.toLowerCase().includes(pattern)).length;
    count += (metadata.qos[selectedHostname] || []).filter(item => item.toLowerCase().includes(pattern)).length;
    count += (metadata.states[selectedHostname] || []).filter(item => item.toLowerCase().includes(pattern)).length;

    return count;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      {/* Always visible: Cluster selection */}
      <div className="filter-group">
        <label htmlFor="hostname">Cluster</label>
        <select
          id="hostname"
          value={selectedHostname}
          onChange={(e) => setSelectedHostname(e.target.value)}
        >
          <option value="">Select cluster...</option>
          {metadata?.hostnames.map((hostname) => (
            <option key={hostname} value={hostname}>
              {hostname}
            </option>
          ))}
        </select>
      </div>

      {/* Always visible: Date range */}
      <div className="filter-group">
        <label htmlFor="start-date">Start Date</label>
        <input
          type="date"
          id="start-date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
          min={dateRange?.min_date}
          max={dateRange?.max_date}
          style={{
            borderColor: startDate && endDate && startDate > endDate ? '#dc3545' : undefined
          }}
        />
      </div>

      <div className="filter-group">
        <label htmlFor="end-date">End Date</label>
        <input
          type="date"
          id="end-date"
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
          min={dateRange?.min_date}
          max={dateRange?.max_date}
          style={{
            borderColor: startDate && endDate && startDate > endDate ? '#dc3545' : undefined
          }}
        />
      </div>

      {/* Date validation warning */}
      {startDate && endDate && startDate > endDate && (
        <div style={{
          padding: '0.75rem',
          background: '#fee',
          border: '1px solid #fcc',
          borderRadius: '4px',
          color: '#c00',
          fontSize: '0.875rem',
          marginTop: '0.5rem',
        }}>
          <strong>Invalid date range:</strong> Start date must be before end date.
        </div>
      )}

      {/* Always visible: Binning Period */}
      <div className="filter-group">
        <label htmlFor="period-type" title="Auto mode selects granularity based on date range">
          Binning Period
        </label>
        <select
          id="period-type"
          value={periodType}
          onChange={(e) => setPeriodType(e.target.value)}
          title="Auto mode selects granularity based on date range"
        >
          <option value="auto">Auto (currently: {currentPeriodType})</option>
          <option value="day">Daily</option>
          <option value="week">Weekly</option>
          <option value="month">Monthly</option>
          <option value="year">Yearly</option>
        </select>
      </div>

      {/* Always visible: Color By */}
      <div className="filter-group">
        <label htmlFor="color-by">Color By</label>
        <select
          id="color-by"
          value={colorBy}
          onChange={(e) => setColorBy(e.target.value)}
        >
          <option value="">None (default)</option>
          <option value="Account">Account</option>
          <option value="Partition">Partition</option>
          <option value="State">State</option>
          <option value="QOS">QoS</option>
          {isAdmin && <option value="User">User</option>}
        </select>
      </div>

      {colorBy === 'Account' && (
        <div className="filter-group">
          <label>Account Name Format</label>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="radio"
                name="account-segments"
                value="0"
                checked={accountSegments === 0}
                onChange={() => setAccountSegments(0)}
              />
              <span>Full names</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="radio"
                name="account-segments"
                value="1"
                checked={accountSegments === 1}
                onChange={() => setAccountSegments(1)}
              />
              <span>First segment</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="radio"
                name="account-segments"
                value="2"
                checked={accountSegments === 2}
                onChange={() => setAccountSegments(2)}
              />
              <span>First two segments</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="radio"
                name="account-segments"
                value="3"
                checked={accountSegments === 3}
                onChange={() => setAccountSegments(3)}
              />
              <span>First three segments</span>
            </label>
          </div>
        </div>
      )}

      {/* Global search - select matching items across all categories */}
      <div className="quick-select-box">
        <label className="quick-select-label">
          Quick Select Across All Categories
        </label>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
          e.g. ewi, gpu, completed...
        </div>
        <div style={{ display: 'flex', gap: '0.35rem', alignItems: 'center' }}>
          <input
            type="text"
            placeholder="Search..."
            value={globalSearch}
            onChange={(e) => setGlobalSearch(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                selectAllMatching();
              }
            }}
            className="quick-select-input"
          />
          <button
            type="button"
            onClick={selectAllMatching}
            disabled={!globalSearch.trim()}
            className="quick-select-button"
            style={{
              background: globalSearch.trim() ? 'var(--success)' : 'var(--border)',
              cursor: globalSearch.trim() ? 'pointer' : 'not-allowed',
            }}
          >
            Select{countMatching() > 0 ? ` (${countMatching()})` : ''}
          </button>
        </div>
        {globalSearch.trim() && countMatching() === 0 && (
          <div style={{ fontSize: '0.7rem', color: 'var(--danger)', marginTop: '0.25rem' }}>
            No matches
          </div>
        )}
      </div>

      {/* Separator and Clear All button */}
      {hasActiveFilters && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
          <button
            type="button"
            onClick={clearAllFilters}
            style={{
              fontSize: '0.75rem',
              padding: '0.3rem 0.6rem',
              background: '#6366f1',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: 500,
            }}
            onMouseOver={(e) => (e.currentTarget.style.background = '#4f46e5')}
            onMouseOut={(e) => (e.currentTarget.style.background = '#6366f1')}
          >
            Clear All Filters
          </button>
        </div>
      )}

      <hr style={{ margin: '0.5rem 0', borderColor: '#dee2e6' }} />

      {/* Collapsible filter categories */}
      {selectedHostname && metadata?.partitions[selectedHostname] && (
        <SearchableCheckboxList
          label="Partitions"
          items={metadata.partitions[selectedHostname]}
          selected={selectedPartitions}
          setSelected={setSelectedPartitions}
          search={partitionSearch}
          setSearch={setPartitionSearch}
          isExpanded={isPartitionsExpanded}
          setIsExpanded={setIsPartitionsExpanded}
        />
      )}

      {selectedHostname && metadata?.accounts[selectedHostname] && (
        <SearchableCheckboxList
          label="Accounts"
          items={metadata.accounts[selectedHostname]}
          selected={selectedAccounts}
          setSelected={setSelectedAccounts}
          search={accountSearch}
          setSearch={setAccountSearch}
          isExpanded={isAccountsExpanded}
          setIsExpanded={setIsAccountsExpanded}
        />
      )}

      {selectedHostname && metadata?.users[selectedHostname] && (
        <SearchableCheckboxList
          label="Users"
          items={metadata.users[selectedHostname]}
          selected={selectedUsers}
          setSelected={setSelectedUsers}
          search={userSearch}
          setSearch={setUserSearch}
          isExpanded={isUsersExpanded}
          setIsExpanded={setIsUsersExpanded}
        />
      )}

      {selectedHostname && metadata?.qos[selectedHostname] && (
        <SearchableCheckboxList
          label="QoS"
          items={metadata.qos[selectedHostname]}
          selected={selectedQos}
          setSelected={setSelectedQos}
          search={qosSearch}
          setSearch={setQosSearch}
          isExpanded={isQosExpanded}
          setIsExpanded={setIsQosExpanded}
        />
      )}

      {selectedHostname && metadata?.states[selectedHostname] && (
        <SearchableCheckboxList
          label="Job States"
          items={metadata.states[selectedHostname]}
          selected={selectedStates}
          setSelected={setSelectedStates}
          search={stateSearch}
          setSearch={setStateSearch}
          isExpanded={isStatesExpanded}
          setIsExpanded={setIsStatesExpanded}
        />
      )}
    </div>
  );
};

export default Filters;
