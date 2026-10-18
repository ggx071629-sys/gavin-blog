param([Parameter(Mandatory=$true)][string]$Control, [Parameter(Mandatory=$true)][string]$Output)
$ErrorActionPreference = 'Stop'
$writer = [System.IO.StreamWriter]::new($Output, $false, [System.Text.UTF8Encoding]::new($false))
try {
  while ($true) {
    $tick = [System.Diagnostics.Stopwatch]::StartNew()
    $state = Get-Content -LiteralPath $Control -Raw | ConvertFrom-Json
    if ($state.stop) { break }
    $tree = @(Get-CimInstance Win32_Process -Property ProcessId,ParentProcessId)
    $rows = @()
    $ownedIds = [System.Collections.Generic.HashSet[int]]::new()
    foreach ($root in $state.roots) {
      $ids = [System.Collections.Generic.HashSet[int]]::new()
      [void]$ids.Add([int]$root.pid)
      do {
        $added = $false
        foreach ($entry in $tree) {
          if ($ids.Contains([int]$entry.ParentProcessId) -and $ids.Add([int]$entry.ProcessId)) { $added = $true }
        }
      } while ($added)
      foreach ($processId in $ids) {
        [void]$ownedIds.Add($processId)
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($null -eq $process) { continue }
        try {
          $rows += @{
            role=$root.role; pid=$process.Id
            started=$process.StartTime.ToUniversalTime().ToString('o')
            cpu_seconds=$process.TotalProcessorTime.TotalSeconds
            working_set=[long]$process.WorkingSet64
            private_bytes=[long]$process.PrivateMemorySize64
            peak_working_set=[long]$process.PeakWorkingSet64
          }
        } finally { $process.Dispose() }
      }
    }
    $memory = Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
    $cpu = Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor -Filter "Name='_Total'"
    foreach ($field in @('AvailableBytes','CommittedBytes','CacheBytes','PagesInputPersec','PagesOutputPersec','PageReadsPersec')) {
      if ($null -eq $memory.$field) { throw "Missing memory counter: $field" }
    }
    if ($null -eq $cpu.PercentProcessorTime) { throw 'Missing system CPU counter' }
    $backgroundWs = [long]0
    $backgroundPrivate = [long]0
    $backgroundCount = 0
    foreach ($other in (Get-Process)) {
      if (-not $ownedIds.Contains($other.Id)) {
        $backgroundWs += [long]$other.WorkingSet64
        $backgroundPrivate += [long]$other.PrivateMemorySize64
        $backgroundCount += 1
      }
      $other.Dispose()
    }
    $sample = @{
      timestamp=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()/1000.0
      phase=$state.phase; processes=@($rows)
      available_bytes=[long]$memory.AvailableBytes
      committed_bytes=[long]$memory.CommittedBytes
      cache_bytes=[long]$memory.CacheBytes
      pages_in_per_second=[long]$memory.PagesInputPersec
      pages_out_per_second=[long]$memory.PagesOutputPersec
      page_reads_per_second=[long]$memory.PageReadsPersec
      system_cpu_percent=[double]$cpu.PercentProcessorTime
      background_working_set_sum=$backgroundWs
      background_private_sum=$backgroundPrivate
      background_process_count=$backgroundCount
      collector_seconds=$tick.Elapsed.TotalSeconds
    }
    $writer.WriteLine(($sample | ConvertTo-Json -Compress -Depth 7))
    $writer.Flush()
    $remaining = 1000 - $tick.ElapsedMilliseconds
    if ($remaining -gt 0) { Start-Sleep -Milliseconds $remaining }
  }
} finally { $writer.Dispose() }
