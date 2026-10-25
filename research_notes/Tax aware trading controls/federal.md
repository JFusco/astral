# US federal tax considerations for ASTRAL

## What should an after-tax model assume for an individual taxable account?

### Takeaway
Use a versioned, configurable tax estimate alongside trading profit, with separate short-term and long-term buckets. Do not infer Joe's marginal rate, filing status, carryforwards, or tax elections from his brokerage account.

### Cited Findings
- Generally, investment capital gains/losses are long-term only after holding **more than one year**; one year or less is short-term. Count from the day after acquisition through disposition. Net short-term gains are ordinary income; losses are netted, and excess net capital losses generally offset up to $3,000 of other income annually ($1,500 married filing separately), with additional losses carried forward. Most capital transactions use Form 8949 and Schedule D; taxable gains can require estimated payments. — [IRS Topic 409](https://www.irs.gov/taxtopics/tc409)
- The opened Topic 409 still labels its dollar rate thresholds **2025**. For **taxable years beginning in 2026**, Rev. Proc. 2025-32 section 4.03 gives maximum 0%/15% capital-gain taxable-income amounts: single/other individuals $49,450/$545,500; married joint/surviving spouse $98,900/$613,700; head of household $66,200/$579,600; married separate $49,450/$306,850. These are total taxable-income thresholds, not a separate untaxed trading-profit allowance. — [IRS Rev. Proc. 2025-32, p. 13](https://www.irs.gov/pub/irs-drop/rp-25-32.pdf)
- NIIT is 3.8% of the lesser of net investment income or MAGI exceeding the applicable threshold: $200,000 single/head of household, $250,000 joint/qualifying surviving spouse, $125,000 married separate. Capital gains generally enter net investment income. Insufficient withholding/estimated payments can create penalties. — [IRS NIIT](https://www.irs.gov/individuals/net-investment-income-tax)

### Inferences
- Proposed design: optimize **expected after-tax terminal wealth subject to risk limits**, and show pretax and estimated after-tax results separately. The user wants profit, so minimizing tax dollars alone is the wrong objective. Paying more tax on materially larger profits can still be better.
- A marginal tax estimate on every profitable trade is only a scenario approximation. Annual gain/loss netting, existing outside-account gains, loss carryforwards, income stacking, and NIIT thresholds can change incremental liability. Treat `tax_profile_unknown` as unavailable estimate, never an implicit 0% rate.
- Add a hypothetical tax reserve to *deployable* cash planning and reporting; it is not an amount withheld by Alpaca unless independently confirmed. Avoid spending all realized gains merely because broker buying power permits it.
- Date boundaries should use a defined tax calendar, acquisition/disposition dates, and explicit leap-year cases; a naive `365 days` threshold can misclassify the more-than-one-year rule.
- The advisor can compare otherwise permissible exits/lots using projected tax cost, expected decay of the trade, transaction costs, and uncertainty. A protective exit, loss halt, reconciliation fix, or risk reduction remains executable even when it realizes a gain or wash-sale loss.

### Gaps
- Joe's filing status, total income, other investment activity, loss carryforwards, account ownership/tax treatment, and professional tax determinations are unknown. These notes assume a personal taxable investment account, not an IRA/entity or established trading business.
- The code should not hardcode a personalized effective combined federal/state rate from this research. Georgia is researched separately.

## How should wash sales be handled across ETFs and crypto?

### Takeaway
Stock/security loss transactions need a 61-day wash-sale check spanning the taxpayer's relevant activity, not just the bot's current positions. Direct crypto needs a reviewed instrument classification; “digital asset” is not a blanket wash-sale exemption.

### Cited Findings
- Section 1091 disallows the relevant loss when substantially identical stock/securities are acquired (or contracted/optioned to acquire) in the period 30 days before through 30 days after a loss sale. The acquired replacement's basis generally reflects the deferred loss. The official Code page opened states currency through Public Law 119-120, **October 7, 2026**. Its operative scope remains stock/securities, including certain contracts/options. — [26 USC 1091](https://uscode.house.gov/us/usc/119-118/t26/s1091/)
- IRS guidance includes replacement purchases in an IRA/Roth IRA and purchases by a spouse or controlled corporation. Generally the disallowed loss increases replacement basis, with a holding-period adjustment, **except** the IRA/Roth purchase case. Substantially-identical determinations depend on facts. — [IRS Publication 550, Wash Sales](https://www.irs.gov/publications/p550)
- The **2026** Form 1099-DA instructions explicitly require wash-sale reporting for tokenized securities treated as stock/securities under section 1091. Broker mandatory reporting for these transactions focuses on matching CUSIPs in the same account; broader cross-account reporting can be optional. — [IRS 2026 Form 1099-DA, Box 1i](https://www.irs.gov/instructions/i1099da)

### Inferences
- Proposed instrument metadata: `tax_classification`, reviewer/source, source date, effective period, `wash_sale_policy`, and `substantially_identical_group`. Same ticker is an obvious detection case; different ticker is not proof of tax distinction. Do not let a model authoritatively declare two similar ETFs safe substitutes.
- For ordinary direct spot crypto that is not stock/security under section 1091, the quoted statutory stock/security rule is not automatically applicable merely because it is crypto. However, IRS property treatment alone does not establish that every digital asset falls outside section 1091. Tokenized stock/security assets are a concrete counterexample. Require reviewed classification; label unresolved assets `review_required` rather than promising deductible immediate rebuy losses.
- Reconcile multiple brokers, strategy sleeves, manual trades, DRIP purchases, spouse/controlled-entity activity, and retirement accounts where applicable. If those feeds are missing, display `wash_sale_scope_incomplete`; broker Form 1099 figures are not proof the taxpayer's entire situation is covered.
- Rebuying after a stock/security loss is not categorically prohibited by the rule. A profit-oriented system can allow a justified trade, forecast the deferral/uncertainty, and record the consequence instead of presenting avoidance of all wash sales as a hard risk rule.
- Loss-sale alerts must remain provisional until the forward 30-day window closes. Purchases in the backward window also matter: merely preventing the next buy does not eliminate existing wash-sale exposure.
- A tax overlay must never postpone an urgent protective sell to avoid a wash sale. No artificial loss-harvesting sequence should be generated from an assumed universal crypto exemption.

### Gaps
- No primary source reviewed supplies a universal “all crypto is exempt” determination, or a universal substantially-identical ETF mapping. These require instrument/fact-specific review.
- The opened codification currency ends October 7, not October 25. This is a research snapshot, not certification that no later enactment exists. Proposed legislative text is not an effective rule: do not enable a crypto wash-sale law change from a bill, commentary, or model inference without enacted authority/effective dates.

## What records and lot-selection rules matter for crypto and ETFs?

### Takeaway
Track tax lots and fees from the start, and identify permissible lots contemporaneously rather than choosing a favorable reconstruction after a sale. The 2026 temporary custodial relief has an expiration date and does not eliminate broker/taxpayer reconciliation.

### Cited Findings
- Digital assets are property. Selling for dollars realizes gain/loss; exchanging materially different digital assets can also realize gain/loss. Qualifying cash acquisition costs increase basis; qualifying cash disposition costs reduce amount realized. Paying transaction services with crypto disposes of the fee units and can produce a separate gain/loss. Transfers between one's own accounts are distinct from taxable sales, and transfer-only costs are not automatically digital-asset transaction costs. — [IRS digital-asset FAQs 48–72 and 81](https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-digital-asset-transactions)
- **Notice 2026-20** extends custodial digital-asset identification relief through **December 31, 2026**. During the relief period, taxpayers may identify units in contemporaneous books/records, or record a sufficiently specific standing order beforehand. This relief does not apply to broker information reporting, so 2026 broker basis/holding dates may differ from taxpayer records. It does not cover noncustodial units. After relief ends, ordinary broker-communication requirements apply unless future authority changes them. The notice's background describes the ordinary default as FIFO within the custodial account if adequate identification is not made. — [IRS Notice 2026-20, sections 2–5](https://www.irs.gov/pub/irs-drop/n-26-20.pdf)
- Wallet/account basis allocation replaced universal allocation under the 2024 rules. Rev. Proc. 2024-28 provides a **conditional transition safe harbor for unused pre-2025 basis**; it is not permission to move arbitrary basis between accounts in 2026. — [IRS Rev. Proc. 2024-28](https://www.irs.gov/pub/irs-drop/rp-24-28.pdf)
- Specific share identification for securities generally requires specifying the shares to the broker at sale/transfer and receiving timely written confirmation. Without adequate identification, FIFO generally applies. Average basis is limited to eligible cases, not a universal fallback. — [IRS Publication 550, Basis of Investment Property](https://www.irs.gov/publications/p550)
- For crypto fees paid from existing units, ordinary lot-selection rules apply, generally FIFO absent adequate identification. When fee units are withheld from newly received different crypto in an exchange, special rules deem the fee units from the acquired units. — [IRS broker-reporting FAQs 11–12](https://www.irs.gov/filing/frequently-asked-questions-about-broker-reporting)
- Covered digital assets generally include units acquired after 2025 in, and continuously held within, the custodial broker account until disposition; basis reporting begins for covered 2026 transactions. Transferred-in units may be noncovered, and customer acquisition information can support ordering without authorizing broker basis reporting. The special 1099-DA “covered security” reporting label must not be confused with section 1091 stock/security classification. — [IRS 2026 Form 1099-DA, Covered security and Basis](https://www.irs.gov/instructions/i1099da)

### Inferences
- Proposed durable ledger per account/wallet and asset: acquisition ID/time/date, exact decimal gross/net units, USD consideration/value source, fees by currency/quantity, allocated USD fee value, original and adjusted basis, broker order/fill/transfer IDs, selected lots and selection timestamp, confirmations/standing instructions, remaining units, tax-rule version, and source lineage. Never derive taxable inventory solely from displayed average entry price.
- Preserve both trade economics and tax-lot accounting. A buy fee deducted in base crypto may reduce tradeable units; a tax model must also account for the fee disposition and correct cost allocation rather than simply charging a dollar P&L fee twice.
- Use FIFO as the initial documented policy where supported, with no claim it is always tax optimal. A future lot optimizer may rank eligible lots by estimated incremental tax and risk impact, but only when the identification mechanism is legally available, the broker can support the applicable instruction, and required records are retained. Highest basis is not universally optimal because holding period and loss usability matter.
- For custodial crypto sold in 2026, log whether valid Notice 2026-20 relief or broker-directed identification was actually used. Schedule a rule-version change for January 1, 2027 and recheck authoritative guidance before then; don't treat relief as permanent.
- Do not implement cross-wallet “highest cost globally.” Transfers should preserve lot lineage and move units without fabricating a sale. Missing transferred basis stays unknown and is flagged, never silently zero or borrowed from another wallet.
- Import Form 1099-B/1099-DA and compare with the ledger; report and explain differences rather than overwriting taxpayer records automatically. Retain acquisition records even where the broker reports proceeds only.

### Gaps
- Alpaca's supported tax-lot direction, confirmations, fee-asset behavior, and tax exports need provider-specific verification before a lot-selection feature is activated. A locally computed “HIFO” number is not proof the sale used those tax lots.
- The digital-asset FAQ opened still references the original 2025 relief dates. Notice 2026-20 is newer operative relief; apply it explicitly instead of treating the FAQ's older dates as the final answer.
- This research does not validate old imported holdings' pre-2025 safe-harbor compliance; preserving purchase/basis evidence and professional review is necessary if such holdings are added.

## Can the bot automatically use trader status, mark-to-market, or special ETF rates?

### Takeaway
No automatic tax-status election. Keep the initial personal-investor model and instrument exceptions visible until a tax professional establishes a different treatment.

### Cited Findings
- Securities trader business status requires seeking daily-movement profit, substantial activity, and continuity/regularity; calling oneself a trader is insufficient. A trader without a valid section 475(f) election generally still uses capital gain/loss and wash-sale rules. A timely valid election generally changes covered trading results to ordinary treatment; investment holdings are excepted. Generally the election is due by the unextended prior-year return deadline, with special procedures for new taxpayers. — [IRS Topic 429](https://www.irs.gov/taxtopics/tc429)
- Section 475 distinguishes securities and commodities and provides separate trader election provisions. Its definitions and record-identification requirements matter; the securities election is not automatically an election for every direct crypto instrument. Elections generally continue until revoked with consent. — [26 USC 475(c), (e), (f)](https://uscode.house.gov/us/usc/119-118/t26/s475/)
- Certain fund capital-gain distributions are long-term regardless of share holding period. Collectibles have special tax treatment; the IRS describes metals/bullion among collectibles. — [IRS Publication 550](https://www.irs.gov/publications/p550)

### Inferences
- Store tax status/elections with explicit effective dates and scope, default `investor`, and require professional/user confirmation before changing the accounting regime. “Agent runs 24/7” and “lots of trades” are not a status decision.
- Classify ETF legal/tax structure before assuming ordinary stock-fund treatment. Precious-metal grantor trusts, commodity products, partnerships, and futures-related funds may need separate rules and issuer tax documentation. Keep them out of a simplified tax optimizer until verified; do not infer an exact fund's treatment from its ticker name.
- Preserve separate identified investment and trading holdings if a professionally advised election is later used. The bot should export evidence, not elect status or file forms on Joe's behalf.

### Gaps
- No finding here establishes that Joe qualifies as a trader, that an election is timely/beneficial, or that any particular spot crypto qualifies for a section 475 commodity election.
- Specific ETF prospectuses/tax structures and any special state adjustments are outside this federal-only research.

## How should paper dogfooding test tax awareness without misrepresenting it?

### Takeaway
Paper tax numbers are hypothetical attribution. They are useful for comparing strategy turnover and lot policies; they are not actual taxes or broker tax records.

### Cited Findings
- Section 1001 computes gain/loss on a sale or other disposition of property from amount realized and adjusted basis and generally recognizes gain/loss on sale/exchange unless another provision applies. — [26 USC 1001](https://uscode.house.gov/us/usc/119-118/t26/s1001/)

### Inferences
- A pure paper simulation with no actual owned asset disposition creates no actual sale gain/loss from the simulated fills. Keep paper tax books separate from live accounts and label them `hypothetical`, including any simulated withholding/reserve.
- Deterministic fixtures should cover: purchase/sale on one-year boundary and leap years; profitable sale with existing loss carryforwards; net capital losses exceeding the annual ordinary-income deduction; short/long netting; partial lots; base-asset and third-asset fees; taxable crypto swaps; nontaxable own-wallet transfer with missing basis; 2026 covered versus transferred noncovered lots; mismatch between 2026 relief books and 1099-DA; January 2027 expiry; tokenized-security wash sale; ordinary spot crypto with unresolved classification; ETF loss followed by manual/DRIP/spouse/IRA replacement; partial replacement units and basis adjustment; and a protective exit that remains permitted despite adverse taxes.
- Show identical strategy runs before tax, after plausible tax profiles, and with tax awareness disabled. Compare terminal wealth, turnover, transaction costs, estimated annual liabilities/reserve, drawdown, and missed/opportunity costs. A tax benefit should never be reported as guaranteed cash when its usability depends on other income or future realization.
- For each tax-sensitive recommendation, record: available lots; estimated tax with assumptions; expected pretax edge/cost; whether the action is discretionary or protective; chosen action and reason; any incomplete external-account scope; and rules/source version. Deterministic evaluation supplies the arithmetic; a model may explain evidence but should not invent basis, tax classifications, or authoritative rates.

### Gaps
- There is no IRS paper-trading-specific ruling relied on here. The simulation boundary is an inference from no real property sale/disposition, not a claim that simulated P&L is an IRS tax record.
- These findings are general federal engineering research as of October 25, 2026, not a personalized tax/legal determination or a complete return-preparation engine.
