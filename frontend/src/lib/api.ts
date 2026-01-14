const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

// Map API
export async function getMapConnections(params?: {
    start_year?: number;
    end_year?: number;
    start_month?: number;
    end_month?: number;
    opo?: string;
}) {
    const searchParams = new URLSearchParams();
    if (params?.start_year) searchParams.set('start_year', params.start_year.toString());
    if (params?.end_year) searchParams.set('end_year', params.end_year.toString());
    if (params?.start_month) searchParams.set('start_month', params.start_month.toString());
    if (params?.end_month) searchParams.set('end_month', params.end_month.toString());
    if (params?.opo) searchParams.set('opo', params.opo);

    const res = await fetch(`${API_BASE}/api/map/connections?${searchParams}`);
    return res.json();
}

export async function getOPOs(params?: {
    start_year?: number;
    end_year?: number;
    start_month?: number;
    end_month?: number;
}) {
    const searchParams = new URLSearchParams();
    if (params?.start_year) searchParams.set('start_year', params.start_year.toString());
    if (params?.end_year) searchParams.set('end_year', params.end_year.toString());
    if (params?.start_month) searchParams.set('start_month', params.start_month.toString());
    if (params?.end_month) searchParams.set('end_month', params.end_month.toString());

    const res = await fetch(`${API_BASE}/api/map/opos?${searchParams}`);
    return res.json();
}

export async function getDateRange() {
    const res = await fetch(`${API_BASE}/api/map/date-range`);
    return res.json();
}

// Survival API
export async function getSurvivalCurves(params?: {
    opos?: string[];
    include_nationwide?: boolean;
}) {
    const searchParams = new URLSearchParams();
    if (params?.opos?.length) searchParams.set('opos', params.opos.join(','));
    if (params?.include_nationwide !== undefined) {
        searchParams.set('include_nationwide', params.include_nationwide.toString());
    }

    const res = await fetch(`${API_BASE}/api/survival/curves?${searchParams}`);
    return res.json();
}

export async function getSurvivalStats(opos?: string[]) {
    const searchParams = new URLSearchParams();
    if (opos?.length) searchParams.set('opos', opos.join(','));

    const res = await fetch(`${API_BASE}/api/survival/stats?${searchParams}`);
    return res.json();
}

export async function getSurvivalOPOs() {
    const res = await fetch(`${API_BASE}/api/survival/opos`);
    return res.json();
}

// Utilization API
export async function getUtilizationSummary(params?: {
    cas_period?: string;
    donor_type?: string;
    opos?: string[];
}) {
    const searchParams = new URLSearchParams();
    if (params?.cas_period) searchParams.set('cas_period', params.cas_period);
    if (params?.donor_type) searchParams.set('donor_type', params.donor_type);
    if (params?.opos?.length) searchParams.set('opos', params.opos.join(','));

    const res = await fetch(`${API_BASE}/api/utilization/summary?${searchParams}`);
    return res.json();
}

export async function getNationalUtilization(params?: {
    cas_period?: string;
    donor_type?: string;
}) {
    const searchParams = new URLSearchParams();
    if (params?.cas_period) searchParams.set('cas_period', params.cas_period);
    if (params?.donor_type) searchParams.set('donor_type', params.donor_type);

    const res = await fetch(`${API_BASE}/api/utilization/national?${searchParams}`);
    return res.json();
}

export async function getUtilizationOPOs() {
    const res = await fetch(`${API_BASE}/api/utilization/opos`);
    return res.json();
}

export async function getLundonScores(opos?: string[]) {
    const searchParams = new URLSearchParams();
    if (opos?.length) searchParams.set('opos', opos.join(','));

    const res = await fetch(`${API_BASE}/api/utilization/lundon?${searchParams}`);
    return res.json();
}
