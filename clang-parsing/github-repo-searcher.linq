<Query Kind="Statements">
  <NuGetReference>LibGit2Sharp</NuGetReference>
  <NuGetReference>Octokit</NuGetReference>
  <Namespace>LibGit2Sharp</Namespace>
  <Namespace>LibGit2Sharp.Handlers</Namespace>
  <Namespace>Octokit</Namespace>
  <Namespace>Octokit.Helpers</Namespace>
  <Namespace>Octokit.Internal</Namespace>
  <Namespace>System.Net</Namespace>
  <Namespace>System.Net.Http</Namespace>
  <Namespace>System.Net.Http.Headers</Namespace>
</Query>

/* Scropt constants */
var outputDir = @"C:\Users\Admin\Downloads\_c-repos";
var repoMinSizeKb = 50;
var repoMaxSizeKb = 100000;
var targetRepoCount = 20;

var client = new GitHubClient(new Octokit.ProductHeaderValue("CompPrehensionApp"));

List<Octokit.Repository> repos = new();
int page = 0;
do
{
	var request = new SearchRepositoriesRequest
	{
		Size = new Octokit.Range(repoMinSizeKb, repoMaxSizeKb),
		Language = Language.C,
		SortField = RepoSearchSort.Stars,
		Order = SortDirection.Descending,
		PerPage = 30,
		Page = page++,
	};
	var requestResult = await client.Search.SearchRepo(request);
	repos.AddRange(requestResult.Items);
} while (repos.Count < targetRepoCount);

"Repos info loaded".Dump();

repos.AsParallel().ForAll(rep =>
{
	var targetRepoPath = Path.Combine(outputDir, string.Join("_", rep.FullName.Split('/')));
	if (Directory.Exists(targetRepoPath))
	{
		$"Dir {targetRepoPath} exists - skipping".Dump();
		return;
	}

	Directory.CreateDirectory(targetRepoPath);

	$"Trying to clone {rep.FullName} to {targetRepoPath}".Dump();
	LibGit2Sharp.Repository.Clone(rep.CloneUrl, targetRepoPath);
});
